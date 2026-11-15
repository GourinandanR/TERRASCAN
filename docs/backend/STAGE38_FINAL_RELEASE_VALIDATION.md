# Stage 38 — Final Release Validation

## Release gate
Run `python scripts/terrascan_release.py` to check required release files, Python syntax, version and selected security controls. After building the archive, run `python scripts/terrascan_release.py --zip PATH_TO_RELEASE_ZIP` to verify ZIP integrity and ensure runtime secrets/database files are not packaged.

## Verification boundaries
The release audit is structural, not a penetration test or scientific validation. Browser E2E requires a configured browser automation runner. The app's optional mandatory login is controlled by `VITE_USER_AUTH_REQUIRED=true`; session state is held in memory and a 30-minute idle timeout signs the user out. Refreshing the page requires signing in again.

## Deployment
Use Docker Compose with `TERRASCAN_USER_AUTH_REQUIRED=true` and `TERRASCAN_AUTH_REQUIRED=false` for the user-session login flow. Do not expose API keys or bearer tokens in public frontend build variables. Use HTTPS and an authenticated reverse proxy in production.

## Scientific integrity
No real planetary data, validated site rankings, predictive accuracy or mission authorization are introduced by these release stages. Existing human evidence review and source provenance requirements remain in force.

## Stage 37 throttle scope
The login/register throttle is process-local memory state. It is useful as a basic guard in a single API worker, but it is not shared across workers or replicas and resets on restart. Use a gateway/WAF or shared rate-limit store for scaled production deployments.
