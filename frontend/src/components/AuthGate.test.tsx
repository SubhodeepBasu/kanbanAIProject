import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AuthGate } from "@/components/AuthGate";

describe("AuthGate", () => {
  it("shows an error on invalid credentials", async () => {
    render(<AuthGate />);

    await userEvent.type(screen.getByPlaceholderText("user"), "wrong");
    await userEvent.type(screen.getByPlaceholderText("password"), "creds");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Invalid credentials"
    );
    expect(
      screen.queryByRole("heading", { name: "Kanban Studio" })
    ).not.toBeInTheDocument();
  });

  it("signs in with valid credentials and allows logout", async () => {
    render(<AuthGate />);

    await userEvent.type(screen.getByPlaceholderText("user"), "user");
    await userEvent.type(screen.getByPlaceholderText("password"), "password");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    expect(
      await screen.findByRole("heading", { name: "Kanban Studio" })
    ).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /log out/i }));

    expect(
      await screen.findByRole("button", { name: /sign in/i })
    ).toBeInTheDocument();
  });
});
