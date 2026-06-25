import { Navigate } from "react-router-dom";

/** Legacy route retained for bookmarks. The maintained editor lives at /app/settings/sap-tcode-mapping. */
export function MappingSettingsPage() {
  return <Navigate replace to="/app/settings/sap-tcode-mapping" />;
}
