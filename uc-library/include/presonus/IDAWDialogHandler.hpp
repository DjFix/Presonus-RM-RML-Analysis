#pragma once

#include "core/public/corevector.h"

namespace Core::Portable {
class Attributes;
}

namespace Presonus {

// Partial source port establishing the original nested scope.
class IDAWDialogHandler {
public:
  class DialogMenu {
  public:
    DialogMenu();
    ~DialogMenu();
    DialogMenu(const DialogMenu &) = delete;
    DialogMenu &operator=(const DialogMenu &) = delete;

    // The original call has no observed side effects. Its return declaration
    // remains unresolved, so the portable interface uses void.
    void debug();
    bool hasChildren() const;
    bool isSeparator() const;

    // The backing attributes must outlive the menu and its children.
    void parse(const Core::Portable::Attributes &attributes);

    const Core::Vector<DialogMenu *> &sourcePortChildren() const;

    const char *sourcePortTitle() const { return title_; }
    const char *sourcePortName() const { return name_; }
    const char *sourcePortCategory() const { return category_; }
    unsigned sourcePortDepth() const { return depth_; }

  private:
    const char *title_ = nullptr;
    const char *name_ = nullptr;
    const char *category_ = nullptr;
    unsigned depth_ = 0;
    Core::Vector<DialogMenu *> children_;
  };
};

} // namespace Presonus
