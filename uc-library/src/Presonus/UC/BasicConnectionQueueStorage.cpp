#include "presonus/uc/basic_connection_runtime.hpp"

namespace presonus::uc {
BasicQueueStorage
makeBasicQueueStorage(void *context,
                      OwnedEventQueueState::ValueProvider provider) {
  return BasicQueueStorage(new OwnedEventQueueState(context, provider));
}
void BasicQueueStorageDeleter::operator()(OwnedEventQueueState *state) const {
  // Actual pinned CCL optional lock/list destruction, never a fake provider.
  delete state;
}
} // namespace presonus::uc
