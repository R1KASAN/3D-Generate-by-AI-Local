import { fireEvent, render, screen } from "@testing-library/react";
import { forwardRef, useImperativeHandle } from "react";
import { describe, expect, it, vi } from "vitest";

import { ModelViewer } from "../../components/model-viewer";

vi.mock("@react-three/fiber", () => ({
  Canvas: ({ children }: { children: React.ReactNode }) => <div data-testid="canvas">{children}</div>,
}));
vi.mock("@react-three/drei", () => ({
  OrbitControls: forwardRef(function OrbitControlsMock(
    props: { enablePan?: boolean; enableRotate?: boolean; enableZoom?: boolean },
    ref,
  ) {
    useImperativeHandle(ref, () => ({ reset: vi.fn(() => resetCalls.push("reset")) }));
    return (
      <div
        data-testid="orbit-controls"
        data-enable-pan={String(props.enablePan)}
        data-enable-rotate={String(props.enableRotate)}
        data-enable-zoom={String(props.enableZoom)}
      />
    );
  }),
  Environment: () => null,
  Html: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  useGLTF: () => ({ scene: null }),
}));

const resetCalls: string[] = [];

describe("ModelViewer", () => {
  it("renders a loading-safe viewer with camera controls", () => {
    resetCalls.length = 0;
    render(<ModelViewer src="/api/v1/jobs/job/model" />);

    expect(screen.getByRole("region", { name: /3d model viewer/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /rotate/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /zoom/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /pan/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /reset camera/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /zoom/i }));
    expect(screen.getByRole("button", { name: /zoom/i })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByTestId("orbit-controls")).toHaveAttribute("data-enable-rotate", "false");
    expect(screen.getByTestId("orbit-controls")).toHaveAttribute("data-enable-zoom", "true");
    expect(screen.getByTestId("orbit-controls")).toHaveAttribute("data-enable-pan", "false");
    fireEvent.click(screen.getByRole("button", { name: /reset camera/i }));
    expect(resetCalls).toEqual(["reset"]);
  });

  it("reports invalid models without exposing internal details", () => {
    render(<ModelViewer src="/invalid.glb" errorMessage="Model unavailable" />);

    expect(screen.getByText("Model unavailable")).toBeInTheDocument();
    expect(screen.queryByText(/prompt_id|storage|traceback/i)).not.toBeInTheDocument();
  });
});
