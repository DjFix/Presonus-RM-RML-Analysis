#pragma once
#include "core/public/corevector.h"

namespace Presonus {
// Intentional source composition with the pinned CCL provider. Native
// inheritance/layout and unobserved filter APIs remain unresolved.
class ChannelGroupFilter {
public:
  explicit ChannelGroupFilter(int count);
  void setVisible(int index, bool visible);
  const Core::Vector<bool> &sourcePortVisibility() const { return visibility_; }

private:
  Core::Vector<bool> visibility_;
};
} // namespace Presonus
