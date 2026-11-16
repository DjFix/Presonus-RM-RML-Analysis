#include "presonus/surface/DisplayManager.hpp"
namespace Presonus {
DisplayManager *DisplayManager::theInstance = nullptr;
DisplayManager::~DisplayManager() {
  theInstance = nullptr;
  const int count = ownedViews_.count();
  for (int i = 0; i < count; ++i)
    delete ownedViews_.at(i);
  ::operator delete(ownedCommandStorage_);
}
DisplayManager *DisplayManager::getInstance() { return theInstance; }
} // namespace Presonus
