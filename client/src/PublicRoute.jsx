import {
  Navigate,
} from "react-router-dom";

import {
  useAuth,
} from "./context/AuthContext";
import PageLoader from "./components/ui/PageLoader";

export default function PublicRoute({
  children,
}) {
  const {
    user,
    loading,
  } = useAuth();

  if (loading) {
    return <PageLoader text="Loading RAGMate..." />;
  }

  if (user) {
    return (
      <Navigate
        to="/dashboard"
        replace
      />
    );
  }

  return children;
}
