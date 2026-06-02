import { useEffect } from "react";

import {
  useUIStore,
} from "../store/useUIStore";

export function useTheme() {
  const darkMode =
    useUIStore(
      (state) =>
        state.darkMode
    );

  useEffect(() => {
    const root =
      document.documentElement;

    if (darkMode) {
      root.classList.add(
        "dark"
      );
    } else {
      root.classList.remove(
        "dark"
      );
    }
  }, [darkMode]);
}