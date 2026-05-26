import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { KanbanBoard } from "@/components/KanbanBoard";
import { initialData } from "@/lib/kanban";

const getFirstColumn = () => screen.getAllByTestId(/column-/i)[0];

const mockFetch = vi.fn();

describe("KanbanBoard", () => {
  beforeEach(() => {
    mockFetch.mockReset();
    mockFetch.mockImplementation((input, init) => {
      const url = typeof input === "string" ? input : input.url;
      if (
        url.startsWith("/api/board") ||
        url.startsWith("http://localhost:8000/api/board")
      ) {
        if (!init || (init as RequestInit).method === undefined) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(initialData),
          } as Response);
        }

        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ status: "ok" }),
        } as Response);
      }
      return Promise.reject(new Error("Unexpected fetch request"));
    });

    vi.stubGlobal("fetch", mockFetch);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders five columns", async () => {
    render(<KanbanBoard user="user" onLogout={() => {}} />);
    expect(await screen.findAllByTestId(/column-/i)).toHaveLength(5);
  });

  it("renames a column", async () => {
    render(<KanbanBoard user="user" onLogout={() => {}} />);
    const column = await screen.findAllByTestId(/column-/i).then((columns) => columns[0]);
    const input = within(column).getByLabelText("Column title");
    await userEvent.clear(input);
    await userEvent.type(input, "New Name");
    expect(input).toHaveValue("New Name");
  });

  it("adds and removes a card", async () => {
    render(<KanbanBoard user="user" onLogout={() => {}} />);
    const column = await screen.findAllByTestId(/column-/i).then((columns) => columns[0]);
    const addButton = within(column).getByRole("button", {
      name: /add a card/i,
    });
    await userEvent.click(addButton);

    const titleInput = within(column).getByPlaceholderText(/card title/i);
    await userEvent.type(titleInput, "New card");
    const detailsInput = within(column).getByPlaceholderText(/details/i);
    await userEvent.type(detailsInput, "Notes");

    await userEvent.click(within(column).getByRole("button", { name: /add card/i }));

    expect(within(column).getByText("New card")).toBeInTheDocument();

    const deleteButton = within(column).getByRole("button", {
      name: /delete new card/i,
    });
    await userEvent.click(deleteButton);

    expect(within(column).queryByText("New card")).not.toBeInTheDocument();
  });
});
