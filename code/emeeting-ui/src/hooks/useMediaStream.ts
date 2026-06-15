import { useEffect, useRef, useState } from "react";

export const useMediaStream = () => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const canvasRef = useRef<HTMLCanvasElement>(document.createElement("canvas"));

  const canUseMedia = !!globalThis.navigator?.mediaDevices?.getUserMedia;
  const [micEnabled, setMicEnabled] = useState(() => canUseMedia);
  const [camEnabled, setCamEnabled] = useState(() => canUseMedia);
  const [mediaReady, setMediaReady] = useState(false);
  /** Bumps whenever a new MediaStream is attached (StrictMode remount / re-acquire) so audio hook re-binds. */
  const [streamEpoch, setStreamEpoch] = useState(0);
  const [error, setError] = useState<string | null>(() => {
    const md = globalThis.navigator?.mediaDevices;
    if (!md?.getUserMedia) {
      return "Камера/микрофон недоступны в этом контексте. Откройте приложение через http://localhost:5173 или используйте HTTPS.";
    }
    return null;
  });

  useEffect(() => {
    const md = globalThis.navigator?.mediaDevices;
    if (!md?.getUserMedia) {
      return;
    }

    md.getUserMedia({ video: true, audio: true })
      .then((stream) => {
        streamRef.current = stream;
        setMediaReady(true);
        setStreamEpoch((e) => e + 1);
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
      })
      .catch((e) => {
        setError(e instanceof Error ? e.message : "Не удалось получить доступ к камере/микрофону");
        setMicEnabled(false);
        setCamEnabled(false);
      });

    return () => {
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  const captureFrame = (): string | null => {
    const video = videoRef.current;
    if (!video || video.videoWidth === 0) return null;

    const vw = video.videoWidth;
    const vh = video.videoHeight;
    /** Downscale for WS → faster DeepFace + tighter realtime bbox overlay */
    const maxDim = 640;
    let dw = vw;
    let dh = vh;
    if (vw > maxDim || vh > maxDim) {
      const s = maxDim / Math.max(vw, vh);
      dw = Math.max(1, Math.round(vw * s));
      dh = Math.max(1, Math.round(vh * s));
    }

    const canvas = canvasRef.current;
    canvas.width = dw;
    canvas.height = dh;

    const ctx = canvas.getContext("2d");
    if (!ctx) return null;

    ctx.drawImage(video, 0, 0, dw, dh);
    return canvas.toDataURL("image/jpeg", 0.52);
  };

  const toggleMic = () => {
    streamRef.current?.getAudioTracks().forEach(
      (t) => (t.enabled = !t.enabled)
    );
    setMicEnabled((v) => !v);
  };

  const toggleCam = () => {
    streamRef.current?.getVideoTracks().forEach(
      (t) => (t.enabled = !t.enabled)
    );
    setCamEnabled((v) => !v);
  };

  return {
    videoRef,
    streamRef,
    mediaReady,
    streamEpoch,
    captureFrame,
    toggleMic,
    toggleCam,
    micEnabled,
    camEnabled,
    error,
  };
};
