#include "presonus/StormMixSceneComponent.hpp"
#include "presonus/panel/PresetNameCache.hpp"
#include "presonus/panel/PresetNameManager.hpp"
#include <cstdlib>
#include <cstring>
#include <fcntl.h>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <linux/landlock.h>
#include <new>
#include <stdexcept>
#include <sys/prctl.h>
#include <sys/syscall.h>
#include <unistd.h>

namespace {
bool failArray = false;
void require(bool condition) {
  if (!condition)
    throw std::runtime_error("scene path replay mismatch");
}
// Test confinement, not an emulated syscall provider. Real CCL/POSIX mkdir
// runs, while Linux denies filesystem writes outside this project-local tree.
void confine() {
  const char *folder = "temp/recovery-work/rolling200-03/storm-paths164/files";
  std::filesystem::create_directories(folder);
  const auto rights =
      LANDLOCK_ACCESS_FS_WRITE_FILE | LANDLOCK_ACCESS_FS_REMOVE_DIR |
      LANDLOCK_ACCESS_FS_REMOVE_FILE | LANDLOCK_ACCESS_FS_MAKE_CHAR |
      LANDLOCK_ACCESS_FS_MAKE_DIR | LANDLOCK_ACCESS_FS_MAKE_REG |
      LANDLOCK_ACCESS_FS_MAKE_SOCK | LANDLOCK_ACCESS_FS_MAKE_FIFO |
      LANDLOCK_ACCESS_FS_MAKE_BLOCK | LANDLOCK_ACCESS_FS_MAKE_SYM;
  landlock_ruleset_attr rules{};
  rules.handled_access_fs = rights;
  int fd = syscall(SYS_landlock_create_ruleset, &rules, sizeof(rules), 0);
  require(fd >= 0);
  int parent = open(folder, O_PATH | O_CLOEXEC);
  require(parent >= 0);
  landlock_path_beneath_attr path{};
  path.allowed_access = rights;
  path.parent_fd = parent;
  require(syscall(SYS_landlock_add_rule, fd, LANDLOCK_RULE_PATH_BENEATH, &path,
                  0) == 0);
  require(prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) == 0);
  require(syscall(SYS_landlock_restrict_self, fd, 0) == 0);
  close(parent);
  close(fd);
}
struct Recall : presonus::scene_port::Recall {
  bool recall(unsigned) const override { return false; }
};
struct Sink : Presonus::Panel::PresetNameCache::ObserverSink {
  void changed(Presonus::Panel::PresetNameCache::Delegate *,
               Presonus::Panel::PresetNameCache &, int, const char *,
               const char *) override {}
  void rebuilt(Presonus::Panel::PresetNameCache::Delegate *,
               Presonus::Panel::PresetNameCache &) override {}
};
struct ManagerAccess : Presonus::Panel::PresetNameManager {
  static Presonus::Panel::PresetNameManager *get() { return theInstance; }
};
} // namespace
void *operator new[](std::size_t size) {
  if (failArray) {
    failArray = false;
    throw std::bad_alloc();
  }
  if (auto *p = std::malloc(size))
    return p;
  throw std::bad_alloc();
}
void operator delete[](void *p) noexcept { std::free(p); }
void operator delete[](void *p, std::size_t) noexcept { std::free(p); }

int main(int argc, char **argv) {
  using namespace Core::Portable;
  using namespace Presonus::Panel;
  try {
    require(argc >= 2);
    const std::string mode(argv[1]);
    if (mode == "provider") {
      require(argc >= 4);
      const std::string operation(argv[2]);
      FileName path(argv[3]);
      if (operation == "setup") {
        require(argc == 5);
        confine();
        if (std::string(argv[4]) == "directory")
          std::filesystem::create_directories(argv[3]);
        else if (std::string(argv[4]) == "file") {
          std::filesystem::create_directories(
              std::filesystem::path(argv[3]).parent_path());
          std::ofstream file(argv[3]);
          file << "existing file\n";
        }
        return 0;
      }
      if (operation == "mkdir") {
        confine();
        std::cout << FileUtils::makeDirectory(path.str()) << '\n';
        return 0;
      }
      if (operation == "directory") {
        std::cout << std::filesystem::is_directory(path.str()) << '\n';
        return 0;
      }
      if (operation == "name") {
        FileName name;
        path.getName(name);
        path = name;
      } else if (operation == "descend") {
        require(argc == 5);
        path.descend(argv[4]);
      } else if (operation == "build") {
        require(argc == 7);
        Sink sink;
        PresetNameCache cache(argv[4], path, 0, 0, sink);
        path = cache.buildFileName(static_cast<unsigned>(std::stoull(argv[5])),
                                   argv[6], "", nullptr, true);
      } else
        require(operation == "construct");
      std::cout << path.str() << '\n';
      return 0;
    }
    confine();
    Recall recall;
    Presonus::StormMixSceneComponent scene(recall);
    scene.setName("scene");
    if (mode == "exception") {
      require(ManagerAccess::get() == nullptr);
      failArray = true;
      bool caught = false;
      try {
        (void)scene.getFileName(1);
      } catch (const std::bad_alloc &) {
        caught = true;
      }
      require(caught && ManagerAccess::get() == nullptr);
      require(scene.getFileName(1).isEmpty());
      require(ManagerAccess::get() != nullptr);
      require(ManagerAccess::get()->sourcePortCacheCapacity() == 10);
      std::cout << "singleton allocation cleanup and retry passed\n";
      return 0;
    }
    require(argc == 8);
    const int binding = std::stoi(argv[2]);
    const unsigned index = static_cast<unsigned>(std::stoull(argv[3]));
    const char *folder = argv[4];
    const char *type = argv[5];
    const int slots = std::stoi(argv[6]);
    const std::string filesystem(argv[7]);
    // All fixture setup is confined too. Long/truncated and missing paths need
    // not have parents, so the real mkdir fails without any fake provider.
    if (filesystem == "directory")
      std::filesystem::create_directories(folder);
    else if (filesystem == "file") {
      std::filesystem::create_directories(
          std::filesystem::path(folder).parent_path());
      std::ofstream file(folder);
      file << "existing file\n";
    }
    Sink sink;
    PresetNameCache cache(type, FileName(folder), slots, 0, sink);
    PresetNameManager borrowed;
    if (binding == 1) {
      require(borrowed.sourcePortAddCache(&cache));
      scene.configurePresetNames(&borrowed);
    } else if (binding == 0)
      scene.configurePresetNames(&borrowed);
    else if (binding == 2) {
      auto &manager = PresetNameManager::instance();
      require(&manager == &PresetNameManager::instance());
      require(manager.sourcePortAddCache(&cache));
    } else
      require(binding == -1);
    auto call = [&]() {
      return mode == "undo" ? scene.getUndoFileName()
                            : scene.getFileName(index);
    };
    auto first = call();
    auto warm = call();
    require(std::strcmp(first.str(), warm.str()) == 0);
    Presonus::StormMixSceneComponent other(recall);
    other.setName("different");
    other.configurePresetNames(&borrowed);
    const bool undo = mode == "undo" || ((index - 1U) & 0x80000000U);
    auto cross = undo ? other.getUndoFileName() : other.getFileName(index);
    if (undo)
      require(std::strcmp(first.str(), cross.str()) == 0);
    else
      require(cross.isEmpty());
    FileName parent(first);
    parent.ascend();
    const bool made = undo && std::filesystem::is_directory(parent.str());
    std::cout << first.str() << '\n'
              << warm.str() << '\n'
              << cross.str() << '\n'
              << made << '\n';
    if (binding == -1)
      require(ManagerAccess::get() != nullptr);
    return 0;
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
