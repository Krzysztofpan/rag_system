from __future__ import annotations

import re

from docling_core.types.doc.document import DoclingDocument
from docling_core.types.doc.items.table.table import TableItem
from docling_core.types.doc.items.table.table_data import TableCell, TableData


def _normalize_header(text: str) -> str:
    return " ".join(text.split()).strip().casefold()


def _merged_first_column(left: str, right: str, description: str) -> str:
    """Pick the best label when two columns were split from one."""
    combined = re.sub(r"\s+", " ", f"{left} {right}").strip()
    if not description.strip():
        return combined

    match = re.match(r"^(.+?)(?=\s+[a-z(])", description.strip())
    if not match:
        return combined

    candidate = match.group(1).strip()
    combined_words = set(combined.casefold().split())
    candidate_words = set(candidate.casefold().split())
    if len(candidate) >= len(combined) and combined_words <= candidate_words:
        return candidate
    return combined


def _find_duplicate_header_column(table: TableItem) -> int | None:
    grid = table.data.grid
    if not grid or table.data.num_cols < 3:
        return None

    header = grid[0]
    for col_idx in range(len(header) - 1):
        left, right = header[col_idx], header[col_idx + 1]
        if not (left.column_header and right.column_header):
            continue
        if _normalize_header(left.text) and _normalize_header(left.text) == _normalize_header(
            right.text
        ):
            return col_idx
    return None


def _merge_table_columns(table: TableItem, left_col: int) -> None:
    right_col = left_col + 1
    grid = table.data.grid
    if not grid or right_col >= len(grid[0]):
        return

    merged_cells: list[TableCell] = []
    seen: set[tuple[int, int]] = set()

    for row in grid:
        left_cell = row[left_col]
        right_cell = row[right_col]
        description = row[right_col + 1].text if right_col + 1 < len(row) else ""
        if left_cell.column_header:
            merged_text = left_cell.text
        else:
            merged_text = _merged_first_column(
                left_cell.text, right_cell.text, description
            )

        origin = (left_cell.start_row_offset_idx, left_cell.start_col_offset_idx)
        if origin not in seen:
            seen.add(origin)
            merged_cells.append(
                left_cell.model_copy(
                    update={
                        "text": merged_text,
                        "col_span": left_cell.col_span + right_cell.col_span,
                        "end_col_offset_idx": right_cell.end_col_offset_idx,
                    }
                )
            )

        for col_idx, cell in enumerate(row):
            if col_idx in (left_col, right_col):
                continue
            origin = (cell.start_row_offset_idx, cell.start_col_offset_idx)
            if origin in seen:
                continue
            seen.add(origin)

            new_start = cell.start_col_offset_idx
            new_end = cell.end_col_offset_idx
            if new_start > right_col:
                new_start -= 1
                new_end -= 1

            merged_cells.append(
                cell.model_copy(
                    update={
                        "start_col_offset_idx": new_start,
                        "end_col_offset_idx": new_end,
                        "col_span": new_end - new_start,
                    }
                )
            )

    table.data = TableData(
        table_cells=merged_cells,
        num_rows=table.data.num_rows,
        num_cols=table.data.num_cols - 1,
        orientation=table.data.orientation,
    )


def repair_split_table_columns(doc: DoclingDocument) -> None:
    """Fallback when TableFormer splits one logical column into two."""
    for table in doc.tables:
        split_at = _find_duplicate_header_column(table)
        if split_at is not None:
            _merge_table_columns(table, split_at)
