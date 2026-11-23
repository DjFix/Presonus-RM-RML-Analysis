#include "presonus/panel/SceneBook.hpp"
namespace Presonus::Panel {
SceneBook::SceneBook(int initialValue)
    : book_(initialValue), dispatchIdentity_(0x32a268) {}
SceneBook::~SceneBook() = default;
} // namespace Presonus::Panel
