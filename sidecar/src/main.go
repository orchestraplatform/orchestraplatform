package main

import (
	"fmt"
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"sync"
	"time"
)

var (
	targetURL    *url.URL
	ownerEmail   string
	lastActivity time.Time
	activityLock sync.Mutex
)

func main() {
	// 1. Configuration from environment
	target := os.Getenv("ORCHESTRA_TARGET_URL") // e.g. http://localhost:8787
	if target == "" {
		log.Fatal("ORCHESTRA_TARGET_URL is required")
	}
	ownerEmail = os.Getenv("ORCHESTRA_OWNER_EMAIL")
	if ownerEmail == "" {
		log.Fatal("ORCHESTRA_OWNER_EMAIL is required")
	}

	listenAddr := os.Getenv("ORCHESTRA_LISTEN_ADDR")
	if listenAddr == "" {
		listenAddr = ":8080"
	}

	var err error
	targetURL, err = url.Parse(target)
	if err != nil {
		log.Fatalf("Invalid target URL: %v", err)
	}

	lastActivity = time.Now()

	// 2. Setup Proxy
	proxy := httputil.NewSingleHostReverseProxy(targetURL)

	requireAuth := os.Getenv("ORCHESTRA_REQUIRE_AUTHENTICATION") != "false"

	// 3. Handlers
	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		// --- Auth Check ---
		if requireAuth {
			// We trust the header from the global Ingress/oauth2-proxy
			userEmail := r.Header.Get("X-Auth-Request-Email")
			if userEmail != ownerEmail {
				log.Printf("Unauthorized access attempt: %s (expected %s)", userEmail, ownerEmail)
				http.Error(w, "Unauthorized: You do not own this workshop.", http.StatusForbidden)
				return
			}
		} else {
			// In dev mode, we log but don't block
			userEmail := r.Header.Get("X-Auth-Request-Email")
			if userEmail != "" && userEmail != ownerEmail {
				log.Printf("DevMode: Access from %s (workshop owner is %s)", userEmail, ownerEmail)
			}
		}

		// --- Activity Tracking ---
		activityLock.Lock()
		lastActivity = time.Now()
		activityLock.Unlock()

		// --- Proxy ---
		proxy.ServeHTTP(w, r)
	})

	// Internal Telemetry/Health endpoints
	http.HandleFunc("/orchestra/health", func(w http.ResponseWriter, r *http.Request) {
		// Readiness check: verify the target application is actually responding.
		// Kubernetes uses this endpoint for the readiness probe, so we must
		// return a non-2xx status until the backend is truly ready.
		client := &http.Client{Timeout: 3 * time.Second}
		resp, err := client.Get(targetURL.String())
		if err != nil {
			http.Error(w, "Target not ready: "+err.Error(), http.StatusServiceUnavailable)
			return
		}
		resp.Body.Close()
		if resp.StatusCode >= 500 {
			http.Error(w, fmt.Sprintf("Target returned %d", resp.StatusCode), http.StatusServiceUnavailable)
			return
		}
		w.WriteHeader(http.StatusOK)
		fmt.Fprintf(w, "OK")
	})

	http.HandleFunc("/orchestra/telemetry", func(w http.ResponseWriter, r *http.Request) {
		activityLock.Lock()
		defer activityLock.Unlock()
		
		w.Header().Set("Content-Type", "application/json")
		fmt.Fprintf(w, `{"last_activity": "%s", "owner": "%s"}`, 
			lastActivity.Format(time.RFC3339), ownerEmail)
	})

	log.Printf("Orchestra Sidecar listening on %s", listenAddr)
	log.Printf("Proxying to %s for owner %s", target, ownerEmail)
	log.Fatal(http.ListenAndServe(listenAddr, nil))
}
