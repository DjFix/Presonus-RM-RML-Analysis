#pragma once
#include "core/portable/coresingleton.h"
#include "core/system/corethread.h"
#include <cstdint>

namespace Core {
struct IPropertyHandler;
}
namespace Presonus::Link {
// Portable state model of RM 13731 Messenger. Singleton inheritance and Lock
// are intentional CCL source adaptations, not recovered ARM object layout.
// The native +12 word still has an unresolved declared type.
class Messenger : public Core::Portable::Singleton<Messenger> {
public:
  Messenger();
  ~Messenger() override;
  // Recovered virtual no-op. Original ordinary return declaration unresolved.
  virtual void init();
  // Portable default hook. Exact original return declaration remains
  // unresolved.
  virtual void start();
  // Portable void choice: original ordinary return declaration unresolved.
  void release();
  // Portable void choice. Handler lifetime stays with its caller.
  void setMsgHandler(Core::IPropertyHandler *handler);
  const Core::IPropertyHandler *boundMsgHandler() const { return msgHandler_; }
  bool releaseRequested() const { return releaseRequested_; }

private:
  Core::IPropertyHandler *msgHandler_ = nullptr;
  std::uint32_t nativeWord12_ = 0;
  bool releaseRequested_ = false;
  Core::Threads::Lock lock_; // replaces legacy CoreLock via actual pinned CCL
};
// Provisional pointer return for the portable port; native ordinary return
// declaration (pointer versus reference/qualification) remains unresolved.
Messenger *getMessenger();
} // namespace Presonus::Link
