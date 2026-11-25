#include "presonus/surface/FatChannelClipboard.hpp"
#include "core/portable/coreparams.h"
#include "presonus/SLChannel.hpp"
namespace Presonus::Surface {
FatChannelClipboard::FatChannelClipboard() : roster_(0, 5) {}

bool FatChannelClipboard::CopyPasteFilter::shouldSave(int type, const char *,
                                                      void *object) const {
  if (type != 1348563553 || !object)
    return true;
  const auto *parameter = static_cast<Core::Portable::Parameter *>(object);
  // Intentional pinned CCL typed-object adaptation of original ARM RTTI cast.
  if (!Core::Portable::core_cast<Presonus::SLChannelBase>(
          parameter->getController()))
    return true;
  return parameter->getTag() == 218;
}
} // namespace Presonus::Surface
