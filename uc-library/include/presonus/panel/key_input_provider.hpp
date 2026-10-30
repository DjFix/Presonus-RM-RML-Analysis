#pragma once
#include "core/portable/coresingleton.h"
namespace presonus::panel {
struct KeyInputProviderAccess;
}
namespace Presonus::Panel {
// Original12byte ARM table: one pure slot, no virtual destructor. Named
// SLMixerHandler override proves method name and constness; bool remains a
// portable return declaration, not inferred from ordinary mangling.
class IKeyInputDelegate {
public:
  virtual bool altKeyPressed() const = 0;

protected:
  ~IKeyInputDelegate() = default;
};
class KeyInputProvider : public Core::Portable::Singleton<KeyInputProvider> {
public:
  virtual bool altKeyPressed() const;

protected:
  KeyInputProvider() =
      default; // Independent source init, no original ctor credit.
private:
  IKeyInputDelegate *delegate_ =
      nullptr; // Borrowed source-port view, not ARM fields.
  friend struct presonus::panel::KeyInputProviderAccess;
};
} // namespace Presonus::Panel
namespace presonus::panel {
// App source-binding API only; the caller owns an actual original-named
// delegate, which must remain live while bound. No fake Core/key backend.
struct KeyInputProviderAccess {
  static void bind(Presonus::Panel::KeyInputProvider &provider,
                   Presonus::Panel::IKeyInputDelegate *delegate) {
    provider.delegate_ = delegate;
  }
};
} // namespace presonus::panel
