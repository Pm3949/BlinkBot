import {
  Navigate,
} from "react-router-dom";

import {
  useAuth,
} from "./context/AuthContext";
import PageLoader from "./components/ui/PageLoader";

export default function ProtectedRoute({
  children,
}) {
  const {
    user,
    loading,
  } = useAuth();

  if (loading) {
    return <PageLoader text="Authenticating..." />;
  }

  if (!user) {
    return (
      <Navigate
        to="/"
        replace
      />
    );
  }

  return children;
}
