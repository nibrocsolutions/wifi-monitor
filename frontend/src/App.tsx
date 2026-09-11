import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { SnapshotProvider } from "./api";
import { Layout } from "./components/Layout";
import { AccessPointPage, ConnectionPage } from "./pages/Connection";
import { DevicesPage, NearbyPage } from "./pages/Discovery";
import { InterfacesPage, InternetPage, SystemPage, TrafficPage } from "./pages/Ops";
import { ConcernsPage, OverviewPage } from "./pages/Overview";

export default function App() {
  return (
    <SnapshotProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<OverviewPage />} />
            <Route path="/concerns" element={<ConcernsPage />} />
            <Route path="/connection" element={<ConnectionPage />} />
            <Route path="/access-point" element={<AccessPointPage />} />
            <Route path="/nearby" element={<NearbyPage />} />
            <Route path="/devices" element={<DevicesPage />} />
            <Route path="/traffic" element={<TrafficPage />} />
            <Route path="/internet" element={<InternetPage />} />
            <Route path="/interfaces" element={<InterfacesPage />} />
            <Route path="/system" element={<SystemPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </SnapshotProvider>
  );
}
