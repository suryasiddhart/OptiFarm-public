{{- define "simulator.name" -}}
{{- default "simulator" .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "simulator.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default "simulator" .Values.nameOverride }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

{{- define "simulator.labels" -}}
app.kubernetes.io/name: {{ include "simulator.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app: simulator
{{- end }}
