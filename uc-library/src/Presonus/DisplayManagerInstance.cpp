#include "presonus/surface/DisplayManager.hpp"
namespace Presonus {
DisplayManager *DisplayManager::theInstance = nullptr;
DisplayManager *DisplayManager::getInstance() { return theInstance; }
} // namespace Presonus
