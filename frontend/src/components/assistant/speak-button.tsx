import { Volume2 } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { SpeechSynthesisService } from "@/services/speech-synthesis";
import { speechLocale } from "@/services/voice-assistant";

/**
 * Reusable "read this aloud" button for every major recommendation section
 * (M3, Task 6): click to play, click again to stop, click after it finishes to
 * replay. Renders nothing when the browser has no speech synthesis so
 * unsupported browsers never see a dead control. Accessible: a real `<button>`
 * with an aria-label and `aria-pressed`, sized for a comfortable touch target.
 */
export function SpeakButton({
  text,
  lang,
  label,
  className,
}: {
  /** Plain-text content to read aloud (localize it before passing it in). */
  text: string;
  /** App language code ("en" / "hi") — resolved to a BCP-47 voice locale. */
  lang?: string;
  /** Accessible name; defaults to a translated "Read aloud". */
  label?: string;
  className?: string;
}) {
  const { t, i18n } = useTranslation();
  const [speaking, setSpeaking] = useState(false);
  const supported = SpeechSynthesisService.isSupported();
  const locale = speechLocale(lang ?? i18n.language);

  if (!supported || !text.trim()) return null;

  const toggle = () => {
    if (speaking) {
      SpeechSynthesisService.cancel();
      setSpeaking(false);
    } else {
      SpeechSynthesisService.speak(text, locale, {
        onEnd: () => setSpeaking(false),
        onError: () => setSpeaking(false),
      });
      setSpeaking(true);
    }
  };

  const accessibleLabel = label ?? t("assistant.speak");

  return (
    <Button
      type="button"
      variant="ghost"
      size="icon"
      aria-label={accessibleLabel}
      aria-pressed={speaking}
      onClick={toggle}
      className={className}
    >
      {speaking ? (
        <Equalizer />
      ) : (
        <Volume2 className="size-4" aria-hidden="true" />
      )}
      <span className="sr-only">
        {speaking ? t("assistant.stopSpeaking") : accessibleLabel}
      </span>
    </Button>
  );
}

/** Speaking indicator: three pulsing bars (equalizer) while TTS is playing. */
function Equalizer() {
  return (
    <span className="flex h-4 items-end gap-0.5" aria-hidden="true">
      <span className="h-3 w-0.5 animate-pulse rounded-sm bg-current [animation-delay:-0.3s]" />
      <span className="h-4 w-0.5 animate-pulse rounded-sm bg-current [animation-delay:-0.15s]" />
      <span className="h-2 w-0.5 animate-pulse rounded-sm bg-current" />
    </span>
  );
}
