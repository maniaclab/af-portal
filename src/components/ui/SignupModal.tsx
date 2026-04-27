"use client";
import { useEffect } from "react";

export default function SignupModal() {
  useEffect(() => {
    // Show the AUP modal on page load
    const initModal = () => {
      const el = document.getElementById("myModal");
      if (el && typeof (window as any).bootstrap !== "undefined") {
        const modal = new (window as any).bootstrap.Modal(el);
        modal.show();
      }
    };
    // Slight delay to ensure Bootstrap JS is loaded
    const timer = setTimeout(initModal, 300);
    return () => clearTimeout(timer);
  }, []);
  return null;
}
