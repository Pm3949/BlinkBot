/* eslint-disable react-refresh/only-export-components */
import {
  createContext,
  useContext,
  useState,
} from "react";

const WorkspaceContext =
  createContext();

export function WorkspaceProvider({
  children,
}) {
  const [
    workspace,
    setWorkspace,
  ] = useState(null);

  return (
    <WorkspaceContext.Provider
      value={{
        workspace,
        setWorkspace,
      }}
    >
      {children}
    </WorkspaceContext.Provider>
  );
}

export function useWorkspace() {
  return useContext(
    WorkspaceContext
  );
}
