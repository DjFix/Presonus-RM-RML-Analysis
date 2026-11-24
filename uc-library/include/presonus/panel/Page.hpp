#pragma once

#include "presonus/panel/Element.hpp"
#include "presonus/panel/TextEntryElement.hpp"

#include <memory>
#include <new>
#include <string>
#include <vector>

namespace Presonus::Panel {

// Portable ownership and storage model. The original constructor and layout
// depend on firmware-specific ElementInfo handling.
class Page {
public:
  // Portable parameter-capable Element interface. It leaves the legacy
  // Element::getParam integer observation carrier unchanged.
  class ParameterElement : public Element {
  public:
    virtual Core::Portable::Parameter *parameter() const = 0;
  };

  // Bind the existing TextEntry provider without assuming its original
  // inheritance. The borrowed TextEntry must outlive this adapter.
  class TextEntrySelection final : public ParameterElement {
  public:
    explicit TextEntrySelection(TextEntryElement &entry) : entry_(entry) {}
    Core::Portable::Parameter *parameter() const override {
      return entry_.getParam();
    }

  private:
    TextEntryElement &entry_;
  };

  using Elements = std::vector<std::unique_ptr<Element>>;

  explicit Page(Elements elements = {}, std::string name = {});
  virtual ~Page();

  // Model the observed unsized receiver deallocation on Linux builds.
  static void operator delete(void *storage) noexcept {
    ::operator delete(storage);
  }

  // The original return declaration is unresolved.
  const char *getName() const;
  // Selection borrows an Element; the caller keeps it alive while selected.
  void activeElement(Element *element);
  Core::Portable::Parameter *getActiveParam() const;
  // Portable hook. The original return declaration and vtable layout remain
  // unresolved.
  virtual void deactivate();
  virtual void recall();
  virtual void store();
  virtual void prepare();
  Element *selectedElement() const noexcept { return activeElement_; }
  bool isEnabled() const noexcept { return enabled_; }

private:
  Elements elements_;
  const std::string name_;
  bool enabled_ = true;
  Element *activeElement_ = nullptr;
};
} // namespace Presonus::Panel
