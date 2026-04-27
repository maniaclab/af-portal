"use client";
import type { FlashMessage } from "@/types";

export default function FlashMessages({ flash }: { flash: FlashMessage }) {
  return (
    <div
      className={`alert alert-${flash.category} alert-dismissible`}
      role="alert"
    >
      {flash.message}
      <button
        type="button"
        className="btn-close"
        data-bs-dismiss="alert"
        aria-label="Close"
      />
    </div>
  );
}
