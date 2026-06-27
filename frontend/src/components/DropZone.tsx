import { useRef, useState, type DragEvent } from "react";

interface DropZoneProps {
  onFiles: (files: File[]) => void;
  accept?: string;
  disabled?: boolean;
}

const ACCEPTED_EXT = [".pdf", ".docx"];

function filterAccepted(files: File[]): File[] {
  return files.filter((f) => {
    const name = f.name.toLowerCase();
    return ACCEPTED_EXT.some((ext) => name.endsWith(ext));
  });
}

export function DropZone({ onFiles, accept = ".pdf,.docx", disabled }: DropZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const handleSelected = (fileList: FileList | null) => {
    if (!fileList) return;
    const accepted = filterAccepted(Array.from(fileList));
    if (accepted.length > 0) onFiles(accepted);
  };

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragging(false);
    if (disabled) return;
    handleSelected(e.dataTransfer.files);
  };

  const onDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (!disabled) setDragging(true);
  };

  const openPicker = () => {
    if (!disabled) inputRef.current?.click();
  };

  return (
    <div
      className={`dropzone${dragging ? " dragging" : ""}`}
      data-testid="dropzone"
      role="button"
      tabIndex={0}
      aria-label="Перетащите файлы сюда или нажмите для выбора. Поддерживаются PDF и DOCX."
      aria-disabled={disabled || undefined}
      onClick={openPicker}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          openPicker();
        }
      }}
      onDrop={onDrop}
      onDragOver={onDragOver}
      onDragLeave={() => setDragging(false)}
    >
      <span className="dropzone-icon" aria-hidden="true">
        📄
      </span>
      <div className="dropzone-title">Перетащите файлы сюда</div>
      <div className="dropzone-hint">
        или нажмите, чтобы выбрать. PDF и DOCX, можно несколько сразу.
      </div>
      <input
        ref={inputRef}
        className="visually-hidden"
        type="file"
        accept={accept}
        multiple
        data-testid="file-input"
        onChange={(e) => {
          handleSelected(e.target.files);
          e.target.value = "";
        }}
      />
    </div>
  );
}
