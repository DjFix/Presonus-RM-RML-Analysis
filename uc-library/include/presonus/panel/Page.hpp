#pragma once

#include "presonus/panel/Element.hpp"
#include "presonus/panel/TextEntryElement.hpp"

#include <memory>
#include <new>
#include <string>
#include <vector>

namespace Presonus::Panel {

// Portable ownership and storage with the observed 96-byte ElementInfo factory.
// Original ARM object layout and unencoded return declarations remain
// unresolved.
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
    explicit TextEntrySelection(TextEntryElement &entry) : entry_(&entry) {}
    TextEntrySelection(const ElementInfo &info,
                       std::unique_ptr<TextEntryElement> entry)
        : ownedEntry_(std::move(entry)), entry_(ownedEntry_.get()) {
      static_cast<Element &>(*this) = Element(info);
    }
    bool editable() override;
    bool needsToDraw() const override;
    void activate(int mode) override;
    void draw(IDisplay &display) override;
    unsigned int next() override;
    unsigned int previous() override;
    unsigned int tap() override;
    unsigned int deltaEncoder(int delta) override;
    void resetCursor();
    TextEntryElement &entry() { return *entry_; }
    Core::Portable::Parameter *parameter() const override {
      return entry_->getParam();
    }

  private:
    std::unique_ptr<TextEntryElement> ownedEntry_;
    TextEntryElement *entry_;
  };

  using Elements = std::vector<std::unique_ptr<Element>>;

  explicit Page(Elements elements = {}, std::string name = {});
  Page(const char *name, const ElementInfo *infos, int count);
  virtual ~Page();
  void add(Element *element);
  virtual void nextField();
  virtual void previousField();
  virtual void tap();
  void deltaEncoder(int delta);
  bool setActiveParam(Core::Portable::Parameter *parameter);
  bool setActiveParam(unsigned int tag);
  virtual void activate(const char *previousPage);
  virtual void update(IDisplay &display);
  void updateParams();
  void setEnabled(bool enabled) { enabled_ = enabled; }
  void setRequiresAltKey(bool required) { requiresAltKey_ = required; }
  bool requiresAltKey() const { return requiresAltKey_; }
  const std::string &previousPageName() const { return previousPage_; }
  const Elements &elements() const { return elements_; }

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
  bool requiresAltKey_ = false;
  bool redraw_ = true;
  std::string previousPage_;
  static Core::Portable::Parameter *parameterOf(Element *element);
};
} // namespace Presonus::Panel
