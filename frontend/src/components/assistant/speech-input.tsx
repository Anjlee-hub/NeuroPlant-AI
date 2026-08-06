import { AlertCircle, Mic, Square } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import {
  type SpeechRecognitionErrorCode,
  type SpeechRecognitionHandle,
  SpeechRecognitionService,
} from "@/services/speech-recognition";
import { speechLocale } from "@/services/voice-assistant";

/**
 * Text input + microphone (M3, Task 6). While listening it streams the live
 * transcript into the field and swaps the mic for a stop control; a final
 * transcript is committed via `onChange`. Mic-permission, no-speech and
 * unsupported-browser states surface as localized alert text below the field
 * (or a disabled mic). All recognition logic lives in SpeechRecognitionService —
 * this component only wires it to the input and translates error codes.
 */
export function SpeechInput({
  value,
  onChange,
  onSubmit,
  placeholder,
  disabled,
  className,
  ariaLabel,
}: {
  value: string;
  onChange: (text: string) => void;
  onSubmit?: () => void;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
  ariaLabel?: string;
}) {
  const { t, i18n } = useTranslation();
  const supported = SpeechRecognitionService.isSupported();
  const [listening, setListening] = useState(false);
  const [errorCode, setErrorCode] = useState<SpeechRecognitionErrorCode | null>(null);
  const [liveText, setLiveText] = useState("");
  const handleRef = useRef<SpeechRecognitionHandle | null>(null);

  const stop = useCallback(() => {
    handleRef.current?.stop();
    handleRef.current = null;
    setListening(false);
    setLiveText("");
  }, []);

  const start = useCallback(() => {
    if (!supported || disabled) return;
    setErrorCode(null);
    setLiveText("");
    const handle = SpeechRecognitionService.create(speechLocale(i18n.language), {
      onStart: () => setListening(true),
      onInterim: setLiveText,
      onFinal: (text) => {
        onChange(text);
        setLiveText("");
      },
      onError: (code) => {
        setErrorCode(code);
        setListening(false);
        setLiveText("");
      },
      onEnd: () => {
        setListening(false);
        setLiveText("");
      },
    });
    handleRef.current = handle;
    handle.start();
  }, [supported, disabled, i18n.language, onChange]);

  // Abort any in-flight session when the component unmounts.
  useEffect(() => () => handleRef.current?.abort(), []);

  const errorKey = errorCode ? `assistant.speechErrors.${errorCode}` : null;

  return (
    <div className={cn("w-full", className)}>
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <Input
            value={listening ? liveText : value}
            onChange={(event) => onChange(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey && onSubmit) {
                event.preventDefault();
                onSubmit();
              }
            }}
            placeholder={listening ? t("assistant.listening") : placeholder}
            aria-label={ariaLabel ?? t("assistant.inputLabel")}
            disabled={disabled}
            className="pr-10"
          />
          <span
            aria-hidden="true"
            className={cn(
              "pointer-events-none absolute right-3 top-1/2 size-2 -translate-y-1/2 rounded-full",
              listening ? "animate-pulse bg-red-500" : "hidden",
            )}
          />
        </div>

        {supported ? (
          <Button
            type="button"
            variant={listening ? "destructive" : "outline"}
            size="icon"
            className="shrink-0"
            aria-label={listening ? t("assistant.stopListening") : t("assistant.speakPrompt")}
            aria-pressed={listening}
            onClick={listening ? stop : start}
            disabled={disabled}
          >
            {listening ? (
              <Square className="size-4" aria-hidden="true" />
            ) : (
              <Mic className="size-4" aria-hidden="true" />
            )}
          </Button>
        ) : (
          <Button
            type="button"
            variant="outline"
            size="icon"
            className="shrink-0"
            aria-label={t("assistant.voiceUnsupported")}
            disabled
          >
            <Mic className="size-4" aria-hidden="true" />
          </Button>
        )}
      </div>

      {errorKey && !listening && (
        <p role="alert" className="mt-1.5 flex items-center gap-1.5 text-xs text-destructive">
          <AlertCircle className="size-3.5 shrink-0" aria-hidden="true" />
          {t(errorKey)}
        </p>
      )}
    </div>
  );
}
