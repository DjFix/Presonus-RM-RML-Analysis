#pragma once

#include "presonus/uc/ClientComponent.hpp"
#include <new>

namespace Presonus {

class DAWFocusChannel : public UC::ClientComponent {
public:
  DAWFocusChannel();
  ~DAWFocusChannel() override;
  void *castTo(int typeId) override;

  // Portable declaration. The original ELF does not encode the return type.
  void init();

  static void operator delete(void *memory) noexcept {
    ::operator delete(memory);
  }

protected:
  Core::Portable::Parameter *focusParameter_;
};

} // namespace Presonus
