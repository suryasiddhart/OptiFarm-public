# Simulator chart

Runs `simulator/` (simulated field devices publishing moisture telemetry to
Mosquitto). It is **not** part of the normal deploy: the main pipeline only
builds and deploys it when run with the `deploySimulator` parameter checked
(and `simulatorEnvironment` = dev or staging; prod is not offered).

## Adding simulated devices

1. Register each device: `POST /api/devices/` (returns `deviceid` + `passkey` once).
2. Store the passkey in Key Vault as `simulator-<deviceid>-<env>`
   (or any name, set as `passkeySecret` on the device):

       az keyvault secret set --vault-name <kv> \
         --name simulator-dev-001-dev --value '<passkey>'

3. List the devices in `pipelines/charts/simulator/values-<env>.yaml`
   (picked up by the pipeline when present):

       devices:
         - deviceid: dev-001
           field_length: 2        # must match the device's field in the app
           field_breadth: 2
           crop_interval: 0.1     # → 20 x 20 moisture cells
           interval_seconds: 30
         - deviceid: dev-002
           field_length: 1
           field_breadth: 1
           crop_interval: 0.25
           send_ts: false

## Connection

Defaults to the in-cluster broker (`mosquitto:1883`, no TLS). Override
`mqtt.host`, `mqtt.port`, `mqtt.tls` (and `mqtt.caFile`) to test the public
TLS endpoint instead, e.g. `mqtt.<vm-ip>.sslip.io:8883`.

## Removing it

Running the pipeline without the flag leaves an existing simulator as is.
To stop it:

    helm uninstall simulator -n optifarm-<env>
