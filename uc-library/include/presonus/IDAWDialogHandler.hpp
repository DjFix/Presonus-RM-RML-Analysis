#pragma once

#include "core/public/corevector.h"

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

    const Core::Vector<DialogMenu *> &sourcePortChildren() const;

  private:
    // The initialized empty receiver is the supported source-port state.
    Core::Vector<DialogMenu *> children_;
  };
};

} // namespace Presonus
