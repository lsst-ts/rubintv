import "@testing-library/jest-dom"
import React from "react"
import { render, screen, fireEvent } from "@testing-library/react"
import DropDownMenu from "../DropDownMenu"

/* global jest, describe, it, expect, beforeEach, afterEach */

describe("DropDownMenu Component", () => {
  const mockItems = [
    { title: "Option 1", value: "value1" },
    { title: "Option 2", value: "value2" },
    { title: "Option 3", value: "value3" },
  ]

  const defaultMenu = {
    key: "test-menu",
    title: "Test Menu",
    items: mockItems,
    selectedItem: null,
  }

  const mockOnItemSelect = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
    // Mock document event listeners
    jest.spyOn(document, "addEventListener")
    jest.spyOn(document, "removeEventListener")
  })

  afterEach(() => {
    // Clean up any remaining event listeners
    jest.restoreAllMocks()
  })

  describe("Rendering", () => {
    it("renders with no selected item", () => {
      render(
        <DropDownMenu menu={defaultMenu} onItemSelect={mockOnItemSelect} />
      )

      const button = screen.getByRole("button")
      expect(button).toBeInTheDocument()
      expect(button).toHaveTextContent("- Select -")
      expect(button).toHaveClass("dropdown-button", "greyed-out")
    })

    it("renders with pre-selected item", () => {
      const menuWithSelection = {
        ...defaultMenu,
        selectedItem: mockItems[1],
      }

      render(
        <DropDownMenu
          menu={menuWithSelection}
          onItemSelect={mockOnItemSelect}
        />
      )

      const button = screen.getByRole("button")
      expect(button).toHaveTextContent("Option 2")
      expect(button).toHaveClass("dropdown-button")
      expect(button).not.toHaveClass("greyed-out")
    })

    it("renders dropdown in closed state initially", () => {
      const { container } = render(
        <DropDownMenu menu={defaultMenu} onItemSelect={mockOnItemSelect} />
      )

      const dropdown = container.querySelector(".dropdown-menu")
      expect(dropdown).toHaveClass("hidden")
    })

    it("renders all menu items", () => {
      render(
        <DropDownMenu menu={defaultMenu} onItemSelect={mockOnItemSelect} />
      )

      const button = screen.getByRole("button")
      fireEvent.click(button)

      mockItems.forEach((item) => {
        expect(screen.getByText(item.title)).toBeInTheDocument()
      })
    })

    it("renders empty menu gracefully", () => {
      const emptyMenu = {
        ...defaultMenu,
        items: [],
      }

      render(<DropDownMenu menu={emptyMenu} onItemSelect={mockOnItemSelect} />)

      const button = screen.getByRole("button")
      fireEvent.click(button)

      const dropdownContent = document.querySelector(".dropdown-content")
      expect(dropdownContent).toBeInTheDocument()
      expect(dropdownContent.children).toHaveLength(0)
    })
  })

  describe("Dropdown Interaction", () => {
    it("opens dropdown when button is clicked", () => {
      const { container } = render(
        <DropDownMenu menu={defaultMenu} onItemSelect={mockOnItemSelect} />
      )

      const button = screen.getByRole("button")
      const dropdown = container.querySelector(".dropdown-menu")

      expect(dropdown).toHaveClass("hidden")

      fireEvent.click(button)

      expect(dropdown).not.toHaveClass("hidden")
    })

    it("closes dropdown when button is clicked again", () => {
      const { container } = render(
        <DropDownMenu menu={defaultMenu} onItemSelect={mockOnItemSelect} />
      )

      const button = screen.getByRole("button")
      const dropdown = container.querySelector(".dropdown-menu")

      // Open dropdown
      fireEvent.click(button)
      expect(dropdown).not.toHaveClass("hidden")

      // Close dropdown
      fireEvent.click(button)
      expect(dropdown).toHaveClass("hidden")
    })

    it("toggles dropdown state correctly", () => {
      const { container } = render(
        <DropDownMenu menu={defaultMenu} onItemSelect={mockOnItemSelect} />
      )

      const button = screen.getByRole("button")
      const dropdown = container.querySelector(".dropdown-menu")

      // Initially closed
      expect(dropdown).toHaveClass("hidden")

      // Open
      fireEvent.click(button)
      expect(dropdown).not.toHaveClass("hidden")

      // Close
      fireEvent.click(button)
      expect(dropdown).toHaveClass("hidden")

      // Open again
      fireEvent.click(button)
      expect(dropdown).not.toHaveClass("hidden")
    })
  })

  describe("Item Selection", () => {
    it("selects item and calls onItemSelect", () => {
      render(
        <DropDownMenu menu={defaultMenu} onItemSelect={mockOnItemSelect} />
      )

      const button = screen.getByRole("button")
      fireEvent.click(button)

      const option1 = screen.getByText("Option 1")
      fireEvent.click(option1)

      expect(mockOnItemSelect).toHaveBeenCalledTimes(1)
      expect(mockOnItemSelect).toHaveBeenCalledWith(mockItems[0])
    })

    it("updates button text after selection", () => {
      render(
        <DropDownMenu menu={defaultMenu} onItemSelect={mockOnItemSelect} />
      )

      const button = screen.getByRole("button")

      // Initially shows "- Select -"
      expect(button).toHaveTextContent("- Select -")

      fireEvent.click(button)
      const option2 = screen.getByText("Option 2")
      fireEvent.click(option2)

      // Should now show selected item
      expect(button).toHaveTextContent("Option 2")
    })

    it("closes dropdown after item selection", () => {
      const { container } = render(
        <DropDownMenu menu={defaultMenu} onItemSelect={mockOnItemSelect} />
      )

      const button = screen.getByRole("button")
      const dropdown = container.querySelector(".dropdown-menu")

      fireEvent.click(button)
      expect(dropdown).not.toHaveClass("hidden")

      const option1 = screen.getByText("Option 1")
      fireEvent.click(option1)

      expect(dropdown).toHaveClass("hidden")
    })

    it("updates button styling after selection", () => {
      render(
        <DropDownMenu menu={defaultMenu} onItemSelect={mockOnItemSelect} />
      )

      const button = screen.getByRole("button")

      // Initially greyed out
      expect(button).toHaveClass("greyed-out")

      fireEvent.click(button)
      const option1 = screen.getByText("Option 1")
      fireEvent.click(option1)

      // Should no longer be greyed out
      expect(button).not.toHaveClass("greyed-out")
      expect(button).toHaveClass("dropdown-button")
    })

    it("works without onItemSelect prop", () => {
      render(<DropDownMenu menu={defaultMenu} />)

      const button = screen.getByRole("button")
      fireEvent.click(button)

      const option1 = screen.getByText("Option 1")

      // Should not throw error
      expect(() => fireEvent.click(option1)).not.toThrow()

      // Button should still update
      expect(button).toHaveTextContent("Option 1")
    })

    it("handles multiple selections correctly", () => {
      render(
        <DropDownMenu menu={defaultMenu} onItemSelect={mockOnItemSelect} />
      )

      const button = screen.getByRole("button")

      // First selection
      fireEvent.click(button)
      fireEvent.click(screen.getByText("Option 1"))
      expect(button).toHaveTextContent("Option 1")

      // Second selection
      fireEvent.click(button)
      fireEvent.click(screen.getByText("Option 3"))
      expect(button).toHaveTextContent("Option 3")

      expect(mockOnItemSelect).toHaveBeenCalledTimes(2)
      expect(mockOnItemSelect).toHaveBeenNthCalledWith(1, mockItems[0])
      expect(mockOnItemSelect).toHaveBeenNthCalledWith(2, mockItems[2])
    })
  })

  describe("Keyboard Interactions", () => {
    it("closes dropdown when Escape key is pressed", () => {
      const { container } = render(
        <DropDownMenu menu={defaultMenu} onItemSelect={mockOnItemSelect} />
      )

      const button = screen.getByRole("button")
      const dropdown = container.querySelector(".dropdown-menu")

      // Open dropdown
      fireEvent.click(button)
      expect(dropdown).not.toHaveClass("hidden")

      // Press Escape
      fireEvent.keyDown(document, { key: "Escape" })
      expect(dropdown).toHaveClass("hidden")
    })

    it("does not close dropdown for other keys", () => {
      const { container } = render(
        <DropDownMenu menu={defaultMenu} onItemSelect={mockOnItemSelect} />
      )

      const button = screen.getByRole("button")
      const dropdown = container.querySelector(".dropdown-menu")

      fireEvent.click(button)
      expect(dropdown).not.toHaveClass("hidden")

      // Press other keys
      fireEvent.keyDown(document, { key: "Enter" })
      fireEvent.keyDown(document, { key: "Space" })
      fireEvent.keyDown(document, { key: "Tab" })

      expect(dropdown).not.toHaveClass("hidden")
    })

    it("only adds escape listener when dropdown is open", () => {
      render(
        <DropDownMenu menu={defaultMenu} onItemSelect={mockOnItemSelect} />
      )

      const button = screen.getByRole("button")

      // Initially closed - no listener should be added
      expect(document.addEventListener).not.toHaveBeenCalledWith(
        "keydown",
        expect.any(Function)
      )

      // Open dropdown - listener should be added
      fireEvent.click(button)
      expect(document.addEventListener).toHaveBeenCalledWith(
        "keydown",
        expect.any(Function)
      )

      // Close dropdown - listener should be removed
      fireEvent.click(button)
      expect(document.removeEventListener).toHaveBeenCalledWith(
        "keydown",
        expect.any(Function)
      )
    })
  })

  describe("Click Outside Behavior", () => {
    it("closes dropdown when clicking outside", () => {
      const { container } = render(
        <div>
          <DropDownMenu menu={defaultMenu} onItemSelect={mockOnItemSelect} />
          <div data-testid="outside">Outside element</div>
        </div>
      )

      const button = screen.getByRole("button")
      const dropdown = container.querySelector(".dropdown-menu")
      const outsideElement = screen.getByTestId("outside")

      // Open dropdown
      fireEvent.click(button)
      expect(dropdown).not.toHaveClass("hidden")

      // Click outside
      fireEvent.click(outsideElement)
      expect(dropdown).toHaveClass("hidden")
    })

    it("does not close when clicking inside dropdown", () => {
      const { container } = render(
        <DropDownMenu menu={defaultMenu} onItemSelect={mockOnItemSelect} />
      )

      const button = screen.getByRole("button")
      const dropdown = container.querySelector(".dropdown-menu")

      fireEvent.click(button)
      expect(dropdown).not.toHaveClass("hidden")

      // Click on dropdown itself (not an item)
      fireEvent.click(dropdown)
      expect(dropdown).not.toHaveClass("hidden")

      // Click on dropdown content
      const dropdownContent = container.querySelector(".dropdown-content")
      fireEvent.click(dropdownContent)
      expect(dropdown).not.toHaveClass("hidden")
    })

    it("only adds click listener when dropdown is open", () => {
      render(
        <DropDownMenu menu={defaultMenu} onItemSelect={mockOnItemSelect} />
      )

      const button = screen.getByRole("button")

      // Initially closed - no listener should be added
      expect(document.addEventListener).not.toHaveBeenCalledWith(
        "click",
        expect.any(Function)
      )

      // Open dropdown - listener should be added
      fireEvent.click(button)
      expect(document.addEventListener).toHaveBeenCalledWith(
        "click",
        expect.any(Function)
      )

      // Close dropdown - listener should be removed
      fireEvent.click(button)
      expect(document.removeEventListener).toHaveBeenCalledWith(
        "click",
        expect.any(Function)
      )
    })

    it("handles click outside with nested elements", () => {
      const { container } = render(
        <div>
          <DropDownMenu menu={defaultMenu} onItemSelect={mockOnItemSelect} />
          <div data-testid="parent">
            <span data-testid="nested">Nested element</span>
          </div>
        </div>
      )

      const button = screen.getByRole("button")
      const dropdown = container.querySelector(".dropdown-menu")

      fireEvent.click(button)
      expect(dropdown).not.toHaveClass("hidden")

      // Click on nested element
      const nestedElement = screen.getByTestId("nested")
      fireEvent.click(nestedElement)
      expect(dropdown).toHaveClass("hidden")
    })
  })

  describe("Props and State Management", () => {
    it("updates when menu.selectedItem prop changes", () => {
      const { rerender } = render(
        <DropDownMenu menu={defaultMenu} onItemSelect={mockOnItemSelect} />
      )

      const button = screen.getByRole("button")
      expect(button).toHaveTextContent("- Select -")

      // Update menu with selected item
      const updatedMenu = {
        ...defaultMenu,
        selectedItem: mockItems[1],
      }

      rerender(
        <DropDownMenu menu={updatedMenu} onItemSelect={mockOnItemSelect} />
      )
      expect(button).toHaveTextContent("Option 2")
    })

    it("handles selectedItem changing from null to item", () => {
      const { rerender } = render(
        <DropDownMenu menu={defaultMenu} onItemSelect={mockOnItemSelect} />
      )

      const button = screen.getByRole("button")
      expect(button).toHaveClass("greyed-out")

      const updatedMenu = {
        ...defaultMenu,
        selectedItem: mockItems[0],
      }

      rerender(
        <DropDownMenu menu={updatedMenu} onItemSelect={mockOnItemSelect} />
      )
      expect(button).not.toHaveClass("greyed-out")
      expect(button).toHaveTextContent("Option 1")
    })

    it("handles selectedItem changing from item to null", () => {
      const menuWithSelection = {
        ...defaultMenu,
        selectedItem: mockItems[0],
      }

      const { rerender } = render(
        <DropDownMenu
          menu={menuWithSelection}
          onItemSelect={mockOnItemSelect}
        />
      )

      const button = screen.getByRole("button")
      expect(button).toHaveTextContent("Option 1")
      expect(button).not.toHaveClass("greyed-out")

      const updatedMenu = {
        ...defaultMenu,
        selectedItem: null,
      }

      rerender(
        <DropDownMenu menu={updatedMenu} onItemSelect={mockOnItemSelect} />
      )
      expect(button).toHaveTextContent("- Select -")
      expect(button).toHaveClass("greyed-out")
    })

    it("handles menu items changing", () => {
      const { rerender } = render(
        <DropDownMenu menu={defaultMenu} onItemSelect={mockOnItemSelect} />
      )

      const button = screen.getByRole("button")
      fireEvent.click(button)

      expect(screen.getByText("Option 1")).toBeInTheDocument()
      expect(screen.getByText("Option 2")).toBeInTheDocument()

      const updatedMenu = {
        ...defaultMenu,
        items: [
          { title: "New Option 1", value: "new1" },
          { title: "New Option 2", value: "new2" },
        ],
      }

      rerender(
        <DropDownMenu menu={updatedMenu} onItemSelect={mockOnItemSelect} />
      )

      expect(screen.queryByText("Option 1")).not.toBeInTheDocument()
      expect(screen.getByText("New Option 1")).toBeInTheDocument()
      expect(screen.getByText("New Option 2")).toBeInTheDocument()
    })
  })

  describe("Event Listener Cleanup", () => {
    it("removes event listeners on component unmount", () => {
      const { unmount } = render(
        <DropDownMenu menu={defaultMenu} onItemSelect={mockOnItemSelect} />
      )

      const button = screen.getByRole("button")
      fireEvent.click(button) // Open dropdown to add listeners

      unmount()

      expect(document.removeEventListener).toHaveBeenCalledWith(
        "click",
        expect.any(Function)
      )
      expect(document.removeEventListener).toHaveBeenCalledWith(
        "keydown",
        expect.any(Function)
      )
    })

    it("handles rapid open/close without memory leaks", () => {
      const { container } = render(
        <DropDownMenu menu={defaultMenu} onItemSelect={mockOnItemSelect} />
      )

      const button = screen.getByRole("button")
      const dropdown = container.querySelector(".dropdown-menu")

      // Rapidly open and close
      for (let i = 0; i < 5; i++) {
        fireEvent.click(button) // Open
        expect(dropdown).not.toHaveClass("hidden")
        fireEvent.click(button) // Close
        expect(dropdown).toHaveClass("hidden")
      }

      // Final state should be closed
      expect(dropdown).toHaveClass("hidden")

      // Keyboard functionality should still work (proving listeners are properly managed)
      fireEvent.click(button) // Open
      fireEvent.keyDown(document, { key: "Escape" })
      expect(dropdown).toHaveClass("hidden")
    })
  })

  describe("Edge Cases", () => {
    it("handles items without titles gracefully", () => {
      const menuWithBadItems = {
        ...defaultMenu,
        items: [
          { title: "", value: "empty" },
          { value: "no-title" },
          { title: "Good Item", value: "good" },
        ],
      }

      render(
        <DropDownMenu menu={menuWithBadItems} onItemSelect={mockOnItemSelect} />
      )

      const button = screen.getByRole("button")
      fireEvent.click(button)

      // Should render all items even with missing/empty titles
      const dropdownItems = document.querySelectorAll(".dropdown-item")
      expect(dropdownItems).toHaveLength(3)
    })

    it("handles items without values", () => {
      const menuWithoutValues = {
        ...defaultMenu,
        items: [{ title: "No Value Item" }, { title: "Another Item" }],
      }

      render(
        <DropDownMenu
          menu={menuWithoutValues}
          onItemSelect={mockOnItemSelect}
        />
      )

      const button = screen.getByRole("button")
      fireEvent.click(button)

      const firstItem = screen.getByText("No Value Item")
      fireEvent.click(firstItem)

      expect(mockOnItemSelect).toHaveBeenCalledWith({ title: "No Value Item" })
    })

    it("handles very long item titles", () => {
      const longTitle =
        "This is a very long item title that might cause layout issues"
      const menuWithLongTitles = {
        ...defaultMenu,
        items: [
          { title: longTitle, value: "long" },
          { title: "Short", value: "short" },
        ],
      }

      render(
        <DropDownMenu
          menu={menuWithLongTitles}
          onItemSelect={mockOnItemSelect}
        />
      )

      const button = screen.getByRole("button")
      fireEvent.click(button)

      expect(screen.getByText(longTitle)).toBeInTheDocument()

      fireEvent.click(screen.getByText(longTitle))
      expect(button).toHaveTextContent(longTitle)
    })

    it("maintains state consistency during rapid interactions", () => {
      const { container } = render(
        <DropDownMenu menu={defaultMenu} onItemSelect={mockOnItemSelect} />
      )

      const button = screen.getByRole("button")
      const dropdown = container.querySelector(".dropdown-menu")

      // Rapid clicks
      fireEvent.click(button)
      fireEvent.click(button)
      fireEvent.click(button)
      fireEvent.click(button)

      // Should end up in closed state
      expect(dropdown).toHaveClass("hidden")

      // One more click should open it
      fireEvent.click(button)
      expect(dropdown).not.toHaveClass("hidden")
    })
  })

  describe("Accessibility", () => {
    it("button has proper role", () => {
      render(
        <DropDownMenu menu={defaultMenu} onItemSelect={mockOnItemSelect} />
      )

      const button = screen.getByRole("button")
      expect(button).toBeInTheDocument()
    })

    it("dropdown items are properly structured", () => {
      render(
        <DropDownMenu menu={defaultMenu} onItemSelect={mockOnItemSelect} />
      )

      const button = screen.getByRole("button")
      fireEvent.click(button)

      const dropdownItems = document.querySelectorAll(".dropdown-item")
      expect(dropdownItems).toHaveLength(mockItems.length)

      dropdownItems.forEach((item, index) => {
        expect(item).toHaveTextContent(mockItems[index].title)
        expect(item.tagName.toLowerCase()).toBe("li")
      })
    })

    it("maintains focus behavior correctly", () => {
      render(
        <DropDownMenu menu={defaultMenu} onItemSelect={mockOnItemSelect} />
      )

      const button = screen.getByRole("button")

      button.focus()
      expect(document.activeElement).toBe(button)

      fireEvent.click(button)
      // Focus should remain manageable
      expect(document.activeElement).toBe(button)
    })
  })
})
