/** Inline SVG icons for meeting UI (no external assets). */
import type { ReactNode } from "react";

type IconProps = {
  className?: string;
  size?: number;
  title?: string;
};

function wrap(
  children: ReactNode,
  { className, size = 20, title }: IconProps,
  viewBox: string
) {
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox={viewBox}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden={title ? undefined : true}
      role={title ? "img" : "presentation"}
    >
      {title ? <title>{title}</title> : null}
      {children}
    </svg>
  );
}

export function IconMicOn(props: IconProps) {
  return wrap(
    <path
      d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm5.3-3c0 3-2.54 5.1-5.3 5.1S6.7 14 6.7 11H5c0 3.41 2.72 6.23 6 6.72V21h2v-3.28c3.28-.49 6-3.31 6-6.72h-1.7z"
      fill="currentColor"
    />,
    props,
    "0 0 24 24"
  );
}

export function IconMicOff(props: IconProps) {
  return wrap(
    <path
      d="M19 11h-1.7c0 .74-.16 1.44-.43 2.05l1.23 1.23c.56-.98.9-2.09.9-3.28zm-4.02.17c0-.06.02-.11.02-.17V5c0-1.66-1.34-3-3-3S9 3.34 9 5v.18l5.98 5.99zM4.27 3 3 4.27l6.01 6.01V11c0 1.66 1.33 3 2.99 3 .22 0 .44-.03.65-.08l5.49 5.49L21 20.73 19.73 22l-7.49-7.49L4.27 3zM12 17c-1.66 0-3-1.34-3-3 0-.08.01-.15.01-.23L14.01 17H12z"
      fill="currentColor"
    />,
    props,
    "0 0 24 24"
  );
}

export function IconCamOn(props: IconProps) {
  return wrap(
    <path
      d="M18 10.48V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-4.48l4 3.02v-11l-4 3.02zM16 18H4V6h12v12z"
      fill="currentColor"
    />,
    props,
    "0 0 24 24"
  );
}

export function IconCamOff(props: IconProps) {
  return wrap(
    <>
      <path
        d="M21 6.5l-4 4V8c0-.55-.45-1-1-1h-3.17L21 17.17V6.5zM3.27 2L2 3.27 4.73 6H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c.21 0 .41-.03.6-.08L19.73 21 21 19.73 3.27 2zM6 18h10.73L6 7.27V18z"
        fill="currentColor"
      />
    </>,
    props,
    "0 0 24 24"
  );
}

export function IconTranscript(props: IconProps) {
  return wrap(
    <>
      <path
        d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zm2 18H6V4h7v5h5v11zM8 12h8v2H8v-2zm0 4h5v2H8v-2z"
        fill="currentColor"
      />
    </>,
    props,
    "0 0 24 24"
  );
}

export function IconChat(props: IconProps) {
  return wrap(
    <path
      d="M20 2H4a2 2 0 0 0-2 2v18l4-4h14a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2zm0 14H6l-2 2V4h16v12z"
      fill="currentColor"
    />,
    props,
    "0 0 24 24"
  );
}

export function IconPeople(props: IconProps) {
  return wrap(
    <>
      <path
        d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z"
        fill="currentColor"
      />
    </>,
    props,
    "0 0 24 24"
  );
}

export function IconScreenShare(props: IconProps) {
  return wrap(
    <path
      d="M20 18c1.1 0 1.99-.9 1.99-2L22 6a2 2 0 0 0-2-2H4c-1.11 0-2 .89-2 2v10a2 2 0 0 0 2 2H0v2h24v-2h-4zm-7-3.53v-2.19c2.78 0 4.61.85 6 2.72-.56-2.35-2.21-4.29-5-4.95V7l-5 3.33L8 7v6.47c-2.78.65-4.44 2.6-5 4.95 1.39-1.87 3.22-2.72 6-2.72z"
      fill="currentColor"
    />,
    props,
    "0 0 24 24"
  );
}

export function IconCallEnd(props: IconProps) {
  return wrap(
    <path
      d="M12 9c-1.6 0-3.15.25-4.6.72v3.1c0 .39-.23.74-.56.9-.98.49-1.87 1.12-2.66 1.85-.18.18-.43.28-.7.28-.28 0-.53-.11-.71-.29L.29 13.08a.996.996 0 0 1 0-1.41c2.73-2.73 6.51-4.42 10.71-4.42 4.2 0 7.99 1.69 10.71 4.42a.996.996 0 0 1 0 1.41l-2.08 2.08c-.18.18-.43.29-.71.29-.27 0-.52-.11-.7-.28a11.27 11.27 0 0 0-2.66-1.85c-.33-.16-.56-.5-.56-.9v-3.1C15.15 9.25 13.6 9 12 9z"
      fill="currentColor"
    />,
    props,
    "0 0 24 24"
  );
}
