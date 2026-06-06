import { AppRoutes } from "./routes";
import { ToastProvider } from "./components/ui/Toast";

export default function App() {
  return (
    <ToastProvider>
      <AppRoutes />
    </ToastProvider>
  );
}
