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

	// 3. Handlers
	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		// --- Auth Check ---
		// We trust the header from the global Ingress/oauth2-proxy
		userEmail := r.Header.Get("X-Auth-Request-Email")
		if userEmail != ownerEmail {
			log.Printf("Unauthorized access attempt: %s (expected %s)", userEmail, ownerEmail)
			http.Error(w, "Unauthorized: You do not own this workshop.", http.StatusForbidden)
			return
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
		// Simple health check: can we reach the target?
		// In a real scenario, we might want to do a lightweight HEAD request
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
