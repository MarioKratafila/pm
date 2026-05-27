import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { KanbanBoard } from "@/components/KanbanBoard";
import { initialData } from "@/lib/kanban";

const mockFetch = vi.fn();

const defaultProps = {
  user: "user",
  token: "test-token",
  boardId: 1,
  boardName: "My Board",
  onLogout: vi.fn(),
  onBackToBoards: vi.fn(),
};

describe("KanbanBoard", () => {
  beforeEach(() => {
    mockFetch.mockReset();
    mockFetch.mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : (input as Request).url;
      if (url.includes("/api/boards/")) {
        if (init?.method === "PUT") {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ status: "ok" }),
          } as Response);
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(initialData),
        } as Response);
      }
      if (url.includes("/api/board")) {
        if (init?.method === "PUT") {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ status: "ok" }),
          } as Response);
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(initialData),
        } as Response);
      }
      return Promise.reject(new Error(`Unexpected fetch: ${url}`));
    });

    vi.stubGlobal("fetch", mockFetch);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders five columns", async () => {
    render(<KanbanBoard {...defaultProps} />);
    expect(await screen.findAllByTestId(/column-/i)).toHaveLength(5);
  });

  it("renames a column", async () => {
    render(<KanbanBoard {...defaultProps} />);
    const column = await screen.findAllByTestId(/column-/i).then((cols) => cols[0]);
    const input = within(column).getByLabelText("Column title");
    await userEvent.clear(input);
    await userEvent.type(input, "New Name");
    expect(input).toHaveValue("New Name");
  });

  it("adds and removes a card", async () => {
    render(<KanbanBoard {...defaultProps} />);
    const column = await screen.findAllByTestId(/column-/i).then((cols) => cols[0]);
    const addButton = within(column).getByRole("button", { name: /add a card/i });
    await userEvent.click(addButton);

    const titleInput = within(column).getByPlaceholderText(/card title/i);
    await userEvent.type(titleInput, "New card");
    const detailsInput = within(column).getByPlaceholderText(/details/i);
    await userEvent.type(detailsInput, "Notes");

    await userEvent.click(within(column).getByRole("button", { name: /add card/i }));
    expect(within(column).getByText("New card")).toBeInTheDocument();

    const deleteButton = within(column).getByRole("button", { name: /delete new card/i });
    await userEvent.click(deleteButton);
    expect(within(column).queryByText("New card")).not.toBeInTheDocument();
  });

  it("shows back to boards button", async () => {
    render(<KanbanBoard {...defaultProps} />);
    await screen.findAllByTestId(/column-/i);
    expect(screen.getByRole("button", { name: /all boards/i })).toBeInTheDocument();
  });

  it("calls onBackToBoards when back button clicked", async () => {
    const onBackToBoards = vi.fn();
    render(<KanbanBoard {...defaultProps} onBackToBoards={onBackToBoards} />);
    await screen.findAllByTestId(/column-/i);
    await userEvent.click(screen.getByRole("button", { name: /all boards/i }));
    expect(onBackToBoards).toHaveBeenCalled();
  });

  it("shows add column button", async () => {
    render(<KanbanBoard {...defaultProps} />);
    await screen.findAllByTestId(/column-/i);
    expect(screen.getByRole("button", { name: /add column/i })).toBeInTheDocument();
  });

  it("adds a new column", async () => {
    render(<KanbanBoard {...defaultProps} />);
    const columnsBefore = await screen.findAllByTestId(/column-/i);
    await userEvent.click(screen.getByRole("button", { name: /add column/i }));
    const columnsAfter = screen.getAllByTestId(/column-/i);
    expect(columnsAfter).toHaveLength(columnsBefore.length + 1);
  });

  it("edits a card", async () => {
    render(<KanbanBoard {...defaultProps} />);
    await screen.findAllByTestId(/column-/i);

    const editButtons = screen.getAllByRole("button", { name: /edit/i });
    await userEvent.click(editButtons[0]);

    const titleInput = screen.getByPlaceholderText("Card title");
    await userEvent.clear(titleInput);
    await userEvent.type(titleInput, "Edited card title");

    await userEvent.click(screen.getByRole("button", { name: /save/i }));
    expect(screen.getByText("Edited card title")).toBeInTheDocument();
  });
});
