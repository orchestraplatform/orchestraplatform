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
oauth2-proxy service URL used by the Traefik ForwardAuth middleware.
*/}}
{{- define "orchestra.oauth2ProxyAuthURL" -}}
{{- printf "http://%s-oauth2-proxy.%s.svc.cluster.local:4180/oauth2/auth" .Release.Name .Release.Namespace }}
{{- end }}

{{/*
oauth2-proxy redirect URL (the callback path oauth2-proxy listens on).
*/}}
{{- define "orchestra.oauth2ProxyRedirectURL" -}}
{{- printf "https://app.%s/oauth2/callback" .Values.global.domain }}
{{- end }}
