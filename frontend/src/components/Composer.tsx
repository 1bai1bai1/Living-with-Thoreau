import { useEffect, useRef, useState } from 'react';

import type { Approval } from '../api';

// The bar at the bottom: what you type (or tap), purchases waiting for your
// say-so, and the way on to the next scene.
export default function Composer(props: {
  mode: 'open' | 'busy' | 'approval' | 'between';
  chips: string[];
  approval: Approval | null;
  notice: string | null;
  onSay: (text: string) => void;
  onApprove: (approved: boolean) => void;
  onContinue: () => void;
}) {
  const [text, setText] = useState('');
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const open = props.mode === 'open';

  useEffect(() => {
    if (open) inputRef.current?.focus({ preventScroll: true });
  }, [open]);

  const send = (value: string) => {
    const t = value.trim();
    if (!t || !open) return;
    props.onSay(t);
    setText('');
  };

  return (
    <div
      className="sticky bottom-0 z-20 border-t border-white/10 bg-night/85 backdrop-blur-md"
      style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}
    >
      <div
        className="mx-auto grid max-w-3xl gap-3 py-3"
        style={{
          paddingLeft: 'max(16px, env(safe-area-inset-left, 0px))',
          paddingRight: 'max(16px, env(safe-area-inset-right, 0px))',
        }}
      >
        {props.notice && (
          <p role="alert" className="rounded border border-amber-300/50 bg-amber-300/10 px-3 py-2 text-sm text-amber-100">
            {props.notice}
          </p>
        )}

        {props.mode === 'approval' && props.approval && (
          <div className="flex flex-wrap items-center justify-between gap-3 rounded border border-amber-200/60 bg-amber-200/10 px-3 py-2.5">
            <p className="min-w-0 text-sm">
              <b className="font-semibold">{props.approval.title}</b> <span className="text-paper/80">{props.approval.detail}</span>
            </p>
            <div className="flex gap-2">
              <button type="button" className="btn-solid" onClick={() => props.onApprove(true)}>
                Pay
              </button>
              <button type="button" className="btn" onClick={() => props.onApprove(false)}>
                Don't
              </button>
            </div>
          </div>
        )}

        {props.mode === 'between' ? (
          <div className="flex justify-end">
            <button type="button" className="btn-solid" onClick={props.onContinue}>
              Continue the story
            </button>
          </div>
        ) : (
          <>
            {open && props.chips.length > 0 && (
              <div className="flex flex-wrap gap-2" aria-label="Suggestions">
                {props.chips.map((chip) => (
                  <button
                    key={chip}
                    type="button"
                    onClick={() => send(chip)}
                    className="rounded-full border border-paper/40 px-3 py-1 text-sm text-paper/90 transition-colors hover:bg-paper hover:text-night"
                  >
                    {chip}
                  </button>
                ))}
              </div>
            )}
            <form
              className="flex items-end gap-2"
              onSubmit={(e) => {
                e.preventDefault();
                send(text);
              }}
            >
              <label htmlFor="say" className="sr-only">
                What do you do?
              </label>
              <textarea
                id="say"
                ref={inputRef}
                rows={1}
                value={text}
                maxLength={500}
                disabled={!open}
                onChange={(e) => setText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    send(text);
                  }
                }}
                placeholder={
                  props.mode === 'busy'
                    ? 'The woods are answering…'
                    : props.mode === 'approval'
                      ? 'Decide about the money first.'
                      : 'What do you do? You can talk to Henry, too.'
                }
                className="max-h-40 min-h-[44px] min-w-0 flex-1 resize-none rounded border border-paper/30 bg-white/[0.04] px-3 py-2.5 text-[15px] text-paper placeholder:text-paper/45 focus:border-paper/70 focus:outline-none disabled:opacity-60"
              />
              <button type="submit" className="btn-solid h-[44px]" disabled={!open || !text.trim()}>
                Send
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}
