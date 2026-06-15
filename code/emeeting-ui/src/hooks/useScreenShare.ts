import { useState } from "react";

export const useScreenShare = () => {
  const [sharing, setSharing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startShare = async () => {
    const md = globalThis.navigator?.mediaDevices;
    if (!md?.getDisplayMedia) {
      setError(
        "Шеринг экрана недоступен в этом контексте. Откройте приложение через http://localhost:5173 или используйте HTTPS."
      );
      return;
    }
    try {
      await md.getDisplayMedia({ video: true });
      setSharing(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось начать демонстрацию экрана");
    }
  };

  return { startShare, sharing, error };
};
