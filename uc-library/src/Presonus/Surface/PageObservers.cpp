#include "presonus/surface/sl_mixer_encoder.hpp"
namespace Presonus::Surface {
void EQPageComponent::removeObserver(IObserver *observer) {
  observers_.remove(observer);
}
void GeqPageComponent::removeObserver(IObserver *observer) {
  observers_.remove(observer);
}
} // namespace Presonus::Surface
