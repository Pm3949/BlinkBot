import {
  useAuth as useContextAuth,
} from "../context/AuthContext";

export default function useAuth() {
  return useContextAuth();
}