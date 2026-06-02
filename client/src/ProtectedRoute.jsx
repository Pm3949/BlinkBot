import {
  Navigate,
} from "react-router-dom";

import {
  useAuth,
} from "./context/AuthContext";
import LoadingSkeleton from "./components/shared/LoadingSkeleton";

export default function ProtectedRoute({
  children,
}) {
  const {
    user,
    loading,
  } = useAuth();

  if (loading) {
    return (
      <div
        className="
        h-screen
        flex
        items-center
        justify-center
      "
      >
        <div className="w-full max-w-md px-6">
          <LoadingSkeleton
            count={2}
            className="h-24"
          />
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <Navigate
        to="/login"
        replace
      />
    );
  }

  return children;
}
