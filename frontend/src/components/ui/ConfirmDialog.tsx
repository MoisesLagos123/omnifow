import { useState, type ReactNode } from "react";
import { Button } from "./Button";
import { Modal } from "./Modal";

interface Props {
  open: boolean;
  title: string;
  description?: ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  destructive?: boolean;
  onConfirm: () => Promise<void> | void;
  onClose: () => void;
}

export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = "Confirmar",
  cancelLabel = "Cancelar",
  destructive = false,
  onConfirm,
  onClose,
}: Props) {
  const [busy, setBusy] = useState(false);

  async function handleConfirm() {
    try {
      setBusy(true);
      await onConfirm();
      onClose();
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={busy ? () => undefined : onClose}
      title={title}
      size="sm"
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={busy}>
            {cancelLabel}
          </Button>
          <Button
            variant="primary"
            onClick={handleConfirm}
            loading={busy}
            data-destructive={destructive ? "" : undefined}
          >
            {confirmLabel}
          </Button>
        </>
      }
    >
      {description}
    </Modal>
  );
}
