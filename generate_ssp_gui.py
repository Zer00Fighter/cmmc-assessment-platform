"""Double-click GUI for validating and generating an Omni Word SSP."""

from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from src.ssp_export import (
    SSPExportMetadata,
    export_ssp,
    validate_ssp_readiness,
    write_readiness_report,
)


class SSPGeneratorApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title("Omni - Generate Word SSP")
        root.geometry("780x390")
        root.resizable(True, False)

        self.workbook = tk.StringVar()
        self.template = tk.StringVar()
        self.output = tk.StringVar()
        self.organization = tk.StringVar()
        self.system = tk.StringVar()
        self.status = tk.StringVar(
            value="Select the workbook, template, and output file."
        )

        frame = ttk.Frame(root, padding=18)
        frame.pack(fill="both", expand=True)
        ttk.Label(
            frame, text="Generate Word Security Plan", font=("Segoe UI", 16, "bold")
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 14))
        self._path_row(frame, 1, "Omni workbook", self.workbook, self._choose_workbook)
        self._path_row(
            frame, 2, "Word SSP template", self.template, self._choose_template
        )
        self._path_row(frame, 3, "Word output", self.output, self._choose_output)
        self._text_row(frame, 4, "Organization override", self.organization)
        self._text_row(frame, 5, "System override", self.system)

        self.require_ready = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frame,
            text="Require completed-SSP readiness (recommended)",
            variable=self.require_ready,
        ).grid(row=6, column=1, sticky="w", pady=(8, 8))
        ttk.Label(frame, textvariable=self.status, wraplength=690).grid(
            row=7, column=0, columnspan=3, sticky="w", pady=(8, 12)
        )
        self.button = ttk.Button(frame, text="Generate Word SSP", command=self._start)
        self.button.grid(row=8, column=1, sticky="w")
        frame.columnconfigure(1, weight=1)

    def _path_row(self, frame, row, label, variable, command) -> None:
        ttk.Label(frame, text=label).grid(
            row=row, column=0, sticky="w", padx=(0, 10), pady=5
        )
        ttk.Entry(frame, textvariable=variable).grid(
            row=row, column=1, sticky="ew", pady=5
        )
        ttk.Button(frame, text="Browse...", command=command).grid(
            row=row, column=2, padx=(10, 0), pady=5
        )

    def _text_row(self, frame, row, label, variable) -> None:
        ttk.Label(frame, text=label).grid(
            row=row, column=0, sticky="w", padx=(0, 10), pady=5
        )
        ttk.Entry(frame, textvariable=variable).grid(
            row=row, column=1, sticky="ew", pady=5
        )

    def _choose_workbook(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("Excel workbooks", "*.xlsx")])
        if path:
            self.workbook.set(path)
            if not self.output.get():
                self.output.set(
                    str(Path(path).with_name("Completed_System_Security_Plan.docx"))
                )

    def _choose_template(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("Word documents", "*.docx")])
        if path:
            self.template.set(path)

    def _choose_output(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".docx", filetypes=[("Word documents", "*.docx")]
        )
        if path:
            self.output.set(path)

    def _start(self) -> None:
        if not all((self.workbook.get(), self.template.get(), self.output.get())):
            messagebox.showerror(
                "Missing information", "Select a workbook, template, and output file."
            )
            return
        self.button.state(["disabled"])
        self.status.set("Validating SSP readiness...")
        parameters = (
            self.workbook.get(),
            self.template.get(),
            self.output.get(),
            self.organization.get(),
            self.system.get(),
            self.require_ready.get(),
        )
        threading.Thread(target=self._generate, args=parameters, daemon=True).start()

    def _generate(
        self,
        workbook_value: str,
        template_value: str,
        output_value: str,
        organization: str,
        system: str,
        require_ready: bool,
    ) -> None:
        try:
            workbook = Path(workbook_value)
            output = Path(output_value)
            report = validate_ssp_readiness(workbook)
            report_path = output.with_suffix(".readiness.txt")
            write_readiness_report(report, report_path)
            if require_ready and not report.ready:
                self.root.after(
                    0,
                    self._blocked,
                    len(report.blockers),
                    len(report.warnings),
                    report_path,
                )
                return
            self.root.after(
                0,
                self.status.set,
                "Generating Word SSP; this may take several minutes...",
            )
            export_ssp(
                template_value,
                workbook,
                output,
                SSPExportMetadata(
                    organization_name=organization,
                    system_name=system,
                ),
            )
            self.root.after(
                0, self._complete, output, report_path, len(report.warnings)
            )
        except Exception as error:
            self.root.after(0, self._failed, str(error))

    def _blocked(self, blockers: int, warnings: int, report_path: Path) -> None:
        self.button.state(["!disabled"])
        self.status.set(
            f"Generation blocked: {blockers} blocker(s), {warnings} warning(s)."
        )
        messagebox.showwarning(
            "SSP not ready",
            f"Completed SSP generation was blocked.\n\nReadiness report:\n{report_path}",
        )

    def _complete(self, output: Path, report_path: Path, warnings: int) -> None:
        self.button.state(["!disabled"])
        self.status.set(f"Completed with {warnings} warning(s): {output}")
        messagebox.showinfo(
            "Word SSP created",
            f"Word SSP:\n{output}\n\nReadiness report:\n{report_path}",
        )

    def _failed(self, message: str) -> None:
        self.button.state(["!disabled"])
        self.status.set("Generation failed. See the error message.")
        messagebox.showerror("Generation failed", message)


def main() -> None:
    root = tk.Tk()
    SSPGeneratorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
