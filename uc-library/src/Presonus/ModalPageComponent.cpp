#include "presonus/ModalPageComponent.hpp"
namespace Presonus {
void *ModalPageComponent::castTo(int classId) {
  return classId == 1299145808 || classId == 1348560741 || classId == 1131375984
             ? this
             : nullptr;
}
} // namespace Presonus
