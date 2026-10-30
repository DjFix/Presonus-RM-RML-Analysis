#include "presonus/surface/mapping_input_routes.hpp"
#include <limits>
#include <stdexcept>
namespace Presonus::Surface {
void MappingComponent::setRadioGroup(int selected, int first, int last,
                                     bool edit) {
  if (first > last)
    return;
  if (last == std::numeric_limits<int>::max())
    throw std::domain_error("terminating original radio range required");
  // Actual CCL bsearch requires nonnull storage even for count0. This source
  // adaptation avoids its invalid empty-list call; original Core not inferred.
  if (countParameters() <= 0)
    return;
  for (int tag = first; tag <= last; ++tag) {
    auto *parameter = getParameterByTag(tag);
    if (!parameter)
      continue;
    const bool current = parameter->getValue() > .5f;
    const bool wanted = tag == selected;
    if (current != wanted)
      parameter->setValue(wanted ? 1.f : 0.f, edit);
  }
}
int MappingComponent::getRadioValue(int first, int last) const {
  if (first > last)
    return -1;
  if (last == std::numeric_limits<int>::max())
    throw std::domain_error("terminating original radio range required");
  if (countParameters() <= 0)
    return -1;
  for (int tag = first; tag <= last; ++tag)
    if (auto *parameter = getParameterByTag(tag);
        parameter && parameter->getValue() > 0.f)
      return tag;
  return -1;
}
} // namespace Presonus::Surface
