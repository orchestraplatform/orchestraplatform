{{/*
Expand the name of the chart.
*/}}
{{- define "orchestra.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "orchestra.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "orchestra.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Selector labels for a component
Usage: include "orchestra.selectorLabels" (dict "component" "api" "context" .)
*/}}
{{- define "orchestra.selectorLabels" -}}
app.kubernetes.io/name: orchestra
app.kubernetes.io/component: {{ .component }}
app.kubernetes.io/instance: {{ .context.Release.Name }}
{{- end }}

{{/*
System node pool placement (GKE Standard, ADR-0005). Two granular helpers so a
pod that already declares a nodeSelector (e.g. the operator's kubernetes.io/os)
can add the pool key WITHOUT emitting a duplicate nodeSelector map. Config-driven
and gated by systemPool.enabled, so single-node/Autopilot/kind installs are
unaffected.

Pod with no existing nodeSelector (api, frontend):
  {{- if .Values.systemPool.enabled }}
  nodeSelector:
    {{- include "orchestra.systemPoolNodeSelector" . | nindent 8 }}
  {{- include "orchestra.systemPoolTolerations" . | nindent 6 }}
  {{- end }}

Pod that already has a nodeSelector (operator): add the entry inside it, then the
tolerations block after it — each gated by the flag.
*/}}
{{- define "orchestra.systemPoolNodeSelector" -}}
{{ .Values.systemPool.nodeSelectorKey }}: {{ .Values.systemPool.nodeSelectorValue | quote }}
{{- end }}
{{- define "orchestra.systemPoolTolerations" -}}
tolerations:
- key: {{ .Values.systemPool.taintKey | quote }}
  operator: Equal
  value: {{ .Values.systemPool.taintValue | quote }}
  effect: {{ .Values.systemPool.taintEffect }}
{{- end }}

{{/*
oauth2-proxy service URL used by the Traefik ForwardAuth middleware.
*/}}
{{- define "orchestra.oauth2ProxyAuthURL" -}}
{{- printf "http://%s-oauth2-proxy.%s.svc.cluster.local:80/oauth2/auth" .Release.Name .Release.Namespace }}
{{- end }}

{{/*
Bundled PostgreSQL (dev/test): service host and derived database URL.
Host matches the Bitnami subchart's primary service name.
*/}}
{{- define "orchestra.postgresqlHost" -}}
{{- printf "%s-postgresql.%s.svc.cluster.local" .Release.Name .Release.Namespace }}
{{- end }}
{{- define "orchestra.postgresqlURL" -}}
{{- printf "postgresql+asyncpg://%s:%s@%s:5432/%s" .Values.postgresql.auth.username .Values.postgresql.auth.password (include "orchestra.postgresqlHost" .) .Values.postgresql.auth.database }}
{{- end }}

{{/*
oauth2-proxy redirect URL (the callback path oauth2-proxy listens on).
*/}}
{{- define "orchestra.oauth2ProxyRedirectURL" -}}
{{- printf "https://app.%s/oauth2/callback" .Values.global.domain }}
{{- end }}
