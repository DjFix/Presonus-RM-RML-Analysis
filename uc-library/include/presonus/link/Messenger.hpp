#pragma once
#include "core/portable/coresingleton.h"
#include "core/system/corethread.h"
#include <cstdint>
namespace Presonus::Link {
// Portable state model of RM 13731 Messenger. Singleton inheritance and Lock
// are intentional CCL source adaptations, not recovered ARM object layout.
// Native +8/+12 zero words have unresolved declared types; no ownership
// inferred.
class Messenger : public Core::Portable::Singleton<Messenger> {
public:
  Messenger();
  ~Messenger() override;
  // Portable void choice: original ordinary return declaration unresolved.
  void release();
  bool releaseRequested() const { return releaseRequested_; }

private:
  std::uint32_t nativeWord8_ = 0;
  std::uint32_t nativeWord12_ = 0;
  bool releaseRequested_ = false;
  Core::Threads::Lock lock_; // replaces legacy CoreLock via actual pinned CCL
};
// Provisional pointer return for the portable port; native ordinary return
// declaration (pointer versus reference/qualification) remains unresolved.
Messenger *getMessenger();
} // namespace Presonus::Link
