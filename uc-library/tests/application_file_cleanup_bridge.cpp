#include "core/portable/corefile.h"
#include "presonus/application/FileCleanup.hpp"
#include <cstdio>
#include <cstdlib>
#include <dirent.h>
#include <filesystem>
#include <iostream>
#include <map>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

using Names = Core::Vector<Core::Portable::FileName>;
namespace {
std::filesystem::path allowed;
std::string allocationLabel;
std::map<void *, std::string> arrayLabels;
std::vector<std::string> filesystemTrace, arrayTrace;
bool recording = false;
std::string decode(const std::string &s) {
  std::string result;
  if (s == "-")
    return result;
  for (std::size_t i = 0; i < s.size(); i += 2)
    result += static_cast<char>(std::stoul(s.substr(i, 2), nullptr, 16));
  return result;
}
std::string encode(const std::string &s) {
  const char digits[] = "0123456789abcdef";
  std::string result;
  for (unsigned char c : s) {
    result += digits[c >> 4];
    result += digits[c & 15];
  }
  return result.empty() ? "-" : result;
}
void guard(const std::string &s) {
  if (s.find('\0') != std::string::npos)
    throw std::runtime_error("NUL in filesystem path");
  auto path = std::filesystem::absolute(s).lexically_normal();
  const auto prefix = allowed.string() + "/";
  if (path.string().compare(0, prefix.size(), prefix) != 0)
    throw std::runtime_error("filesystem path outside owned fixture root");
}
std::string field(std::istringstream &input) {
  std::string s;
  if (!(input >> s))
    throw std::runtime_error("missing protocol argument");
  return decode(s);
}
} // namespace

extern "C" int __real_remove(const char *);
extern "C" int __real_rmdir(const char *);
extern "C" FILE *__real_fopen(const char *, const char *);
extern "C" DIR *__real_opendir(const char *);
extern "C" void *__real__Znam(std::size_t);
extern "C" void __real__ZdaPv(void *);
extern "C" void __real__ZdaPvm(void *, std::size_t);
extern "C" void explicitCleanupD1(void *) asm("_ZN8Presonus11FileCleanupD1Ev");
namespace {
void filesystemGuard(const char *path) {
  try {
    if (allowed.empty())
      throw std::runtime_error("fixture guard not initialized");
    guard(path);
  } catch (const std::exception &error) {
    std::cerr << "BLOCKED fixture filesystem operation: " << error.what()
              << '\n';
    std::abort();
  }
}
} // namespace
extern "C" void *__wrap__Znam(std::size_t size) {
  void *p = __real__Znam(size);
  if (!allocationLabel.empty())
    arrayLabels[p] = allocationLabel;
  return p;
}
namespace {
void observeArrayDelete(void *p) {
  auto found = arrayLabels.find(p);
  if (found != arrayLabels.end()) {
    if (recording)
      arrayTrace.push_back(found->second);
    arrayLabels.erase(found);
  }
}
} // namespace
extern "C" void __wrap__ZdaPv(void *p) {
  observeArrayDelete(p);
  __real__ZdaPv(p);
}
extern "C" void __wrap__ZdaPvm(void *p, std::size_t size) {
  observeArrayDelete(p);
  __real__ZdaPvm(p, size);
}
extern "C" int __wrap_remove(const char *path) {
  filesystemGuard(path);
  const int result = __real_remove(path);
  if (recording)
    filesystemTrace.push_back(std::string("remove ") + encode(path) + " " +
                              std::to_string(result == 0));
  return result;
}
extern "C" int __wrap_rmdir(const char *path) {
  filesystemGuard(path);
  const int result = __real_rmdir(path);
  if (recording)
    filesystemTrace.push_back(std::string("rmdir ") + encode(path) + " " +
                              std::to_string(result == 0));
  return result;
}
extern "C" FILE *__wrap_fopen(const char *path, const char *mode) {
  filesystemGuard(path);
  return __real_fopen(path, mode);
}
extern "C" DIR *__wrap_opendir(const char *path) {
  filesystemGuard(path);
  return __real_opendir(path);
}

int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  allowed = std::filesystem::absolute(argv[1]).lexically_normal();
  if (!std::filesystem::is_directory(allowed))
    return 3;
  std::map<unsigned, std::unique_ptr<Names>> vectors;
  std::map<unsigned, std::unique_ptr<Core::Portable::FileIterator>> iterators;
  std::unique_ptr<Presonus::FileCleanup> native;
  unsigned next = 1;
  std::string line;
  while (std::getline(std::cin, line)) {
    try {
      std::istringstream input(line);
      std::string operation;
      input >> operation;
      unsigned id = 0;
      if (operation == "reset") {
        recording = false;
        native.reset();
        iterators.clear();
        vectors.clear();
        next = 1;
        std::cout << "OK";
      } else if (operation == "trace_begin") {
        filesystemTrace.clear();
        arrayTrace.clear();
        recording = true;
        std::cout << "OK";
      } else if (operation == "trace_get") {
        std::cout << filesystemTrace.size();
        for (const auto &item : filesystemTrace)
          std::cout << ' ' << encode(item);
        std::cout << ' ' << arrayTrace.size();
        for (const auto &item : arrayTrace)
          std::cout << ' ' << encode(item);
      } else if (operation == "vector_new") {
        id = next++;
        vectors.emplace(id, std::make_unique<Names>(0, 5));
        std::cout << id;
      } else if (operation == "vector_add") {
        input >> id;
        const auto name = field(input);
        allocationLabel = "peer:" + std::to_string(id);
        const bool added =
            vectors.at(id)->add(Core::Portable::FileName(name.c_str()));
        allocationLabel.clear();
        std::cout << added;
      } else if (operation == "vector_snapshot") {
        input >> id;
        auto &v = *vectors.at(id);
        std::cout << v.count();
        for (int i = 0; i < v.count(); ++i)
          std::cout << ' ' << encode(v.at(i).str());
      } else if (operation == "vector_destroy") {
        input >> id;
        if (!vectors.erase(id))
          throw std::runtime_error("unknown vector");
        std::cout << "OK";
      } else if (operation == "descend") {
        const auto base = field(input), child = field(input);
        Core::Portable::FileName path(base.c_str());
        path.descend(child.c_str());
        guard(path.str());
        std::cout << encode(path.str());
      } else if (operation == "file_exists" || operation == "dir_exists" ||
                 operation == "delete_file" ||
                 operation == "remove_directory") {
        const auto path = field(input);
        guard(path);
        if (operation == "file_exists")
          std::cout << Core::Portable::FileUtils::fileExists(path.c_str());
        else if (operation == "dir_exists")
          std::cout << Core::Portable::FileUtils::dirExists(path.c_str());
        else if (operation == "delete_file")
          std::cout << Core::Portable::FileUtils::deleteFile(path.c_str());
        else
          std::cout << Core::Portable::FileUtils::removeDirectory(path.c_str());
      } else if (operation == "iterator_new") {
        const auto path = field(input);
        guard(path);
        id = next++;
        iterators.emplace(
            id, std::make_unique<Core::Portable::FileIterator>(path.c_str()));
        std::cout << id;
      } else if (operation == "iterator_next") {
        input >> id;
        const auto *entry = iterators.at(id)->next();
        if (!entry)
          std::cout << "NONE";
        else
          std::cout << "ENTRY " << encode(entry->name.str()) << ' '
                    << entry->directory << ' ' << entry->hidden;
      } else if (operation == "iterator_destroy") {
        input >> id;
        if (!iterators.erase(id))
          throw std::runtime_error("unknown iterator");
        std::cout << "OK";
      } else if (operation == "native_new") {
        const auto path = field(input);
        guard(path);
        native = std::make_unique<Presonus::FileCleanup>(
            Core::Portable::FileName(path.c_str()));
        std::cout << "OK";
      } else if (operation == "native_add_file" ||
                 operation == "native_add_directory") {
        if (!native)
          throw std::runtime_error("native object missing");
        const auto name = field(input);
        Core::Portable::FileName path(name.c_str());
        allocationLabel =
            operation == "native_add_file" ? "files" : "directories";
        const bool added = operation == "native_add_file"
                               ? native->addFileToRemove(path)
                               : native->addDirectoryToRemove(path);
        allocationLabel.clear();
        std::cout << added;
      } else if (operation == "native_cleanup") {
        if (!native)
          throw std::runtime_error("native object missing");
        std::cout << native->cleanup();
      } else if (operation == "native_destroy") {
        auto *object = native.release();
        if (object) {
          explicitCleanupD1(object);
          ::operator delete(object);
        }
        std::cout << "OK";
      } else if (operation == "quit") {
        std::cout << "OK\n" << std::flush;
        return 0;
      } else
        throw std::runtime_error("unknown protocol operation");
      std::cout << '\n' << std::flush;
    } catch (const std::exception &error) {
      std::cout << "ERROR " << encode(error.what()) << '\n' << std::flush;
      return 4;
    }
  }
}
