import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import os
import xlsxwriter
from modules.utilities import time_function
from .constants import CROSS_SECTION_NUMBER, STATION, ELEVATION, MAX_STAGE, MAX_DISCHARGE

@time_function
def create_channel_excel(file_path, combined_df):
    output_excel_path = os.path.join(file_path, 'flo2d_plots', 'channel_results.xlsx')
    with pd.ExcelWriter(output_excel_path, engine='xlsxwriter') as writer:
        # Full summary sheet
        combined_df.to_excel(writer, sheet_name='Full Summary', index=False)
        
        # Unique cross section summary sheet
        unique_df = combined_df.drop_duplicates(subset=[CROSS_SECTION_NUMBER])
        unique_df.to_excel(writer, sheet_name='Unique Cross Section Summary', index=False)
    
    print(f"Excel file created: {output_excel_path}")

@time_function
def create_channel_plots(combined_df, output_pdf_path):
    unique_cross_sections = sorted(combined_df[CROSS_SECTION_NUMBER].unique())
    cs_data_dict = {
        cs_num: combined_df[combined_df[CROSS_SECTION_NUMBER] == cs_num]
        for cs_num in unique_cross_sections
    }

    with PdfPages(output_pdf_path) as pdf:
        for i in range(0, len(unique_cross_sections), 4):
            fig, axs = plt.subplots(2, 2, figsize=(8.5, 11))
            fig.subplots_adjust(hspace=0.5, wspace=0.3)
            axs = axs.flatten()

            page_sections = unique_cross_sections[i : i + 4]
            for j, cross_section_number in enumerate(page_sections):
                cs_data = cs_data_dict[cross_section_number]
                station = cs_data[STATION].to_numpy()
                elevation = cs_data[ELEVATION].to_numpy()

                ax = axs[j]
                ax.plot(
                    station,
                    elevation,
                    color="black",
                    linewidth=1.5,
                    label="Ground Profile",
                    zorder=10,
                )

                max_stage = cs_data[MAX_STAGE].max()
                max_discharge = cs_data[MAX_DISCHARGE].max()

                if pd.notna(max_stage):
                    start = station[0] if max_stage >= elevation[0] else None
                    end = station[-1] if max_stage >= elevation[-1] else None
                    inter = []
                    for k in range(len(station) - 1):
                        e1, e2 = elevation[k], elevation[k + 1]
                        diff = e2 - e1
                        between = (e1 < max_stage <= e2) or (e2 < max_stage <= e1)
                        if between and abs(diff) > 1e-9:
                            xi = station[k] + (station[k + 1] - station[k]) * (
                                (max_stage - e1) / diff
                            )
                            inter.append(xi)
                        elif between and abs(diff) < 1e-9 and abs(e1 - max_stage) < 1e-9:
                            inter.extend([station[k], station[k + 1]])
                    inter = sorted(set(inter))
                    if start is None and inter:
                        start = inter[0]
                    if end is None and inter:
                        end = inter[-1]
                    if start is not None and end is not None and end > start:
                        ax.fill_between(
                            station,
                            elevation,
                            max_stage,
                            where=(elevation <= max_stage)
                            & (station >= start)
                            & (station <= end),
                            interpolate=True,
                            color="lightblue",
                            alpha=0.7,
                            zorder=5,
                        )
                        ax.plot(
                            [start, end],
                            [max_stage, max_stage],
                            color="blue",
                            linewidth=1.5,
                            label="Max Water Surface",
                            zorder=15,
                        )

                ax.set_title(f"Cross-Section {cross_section_number}", fontsize=10)
                ax.set_xlabel("Station (ft)", fontsize=8)
                ax.set_ylabel("Elevation (ft)", fontsize=8)

                lines = []
                if pd.notna(max_discharge):
                    lines.append(f"Max Q: {max_discharge:.0f} cfs")
                if pd.notna(max_stage):
                    lines.append(f"Max Stage: {max_stage:.2f} ft")
                if lines:
                    ax.text(
                        0.03,
                        0.97,
                        "\n".join(lines),
                        transform=ax.transAxes,
                        va="top",
                        fontsize=7,
                        bbox=dict(
                            boxstyle="round,pad=0.3",
                            facecolor="white",
                            alpha=0.8,
                            edgecolor="lightgray",
                        ),
                    )

                ax.grid(True, linestyle=":", alpha=0.5, color="gray")
                min_e = elevation.min()
                max_e = max(
                    elevation.max(), max_stage if pd.notna(max_stage) else elevation.max()
                )
                buf = (max_e - min_e) * 0.1 if max_e > min_e else 1.0
                ax.set_ylim(min_e - buf, max_e + buf)
                ax.tick_params(axis="both", which="major", labelsize=7)
                handles, labels = ax.get_legend_handles_labels()
                if "Max Water Surface" in labels:
                    ax.legend(handles, labels, fontsize=7, loc="lower right", framealpha=0.7)
                else:
                    ax.legend().remove()

            for j in range(len(page_sections), 4):
                fig.delaxes(axs[j])

            pdf.savefig(fig)
            plt.close(fig)

    print(f"PDF file created: {output_pdf_path}")

@time_function
def channel_spreadsheet_and_plots(file_path, channel_data):
    out_folder_path = os.path.join(file_path, 'flo2d_plots')
    os.makedirs(out_folder_path, exist_ok=True)
    
    create_channel_excel(file_path, channel_data)
    create_channel_plots(channel_data, os.path.join(out_folder_path, 'channel_plots.pdf'))
