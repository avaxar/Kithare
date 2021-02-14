#pragma once

#include "utility/std.hpp"
#include "utility/string.hpp"

#include "lexer/type.hpp"
#include "lexer/value.hpp"
#include "lexer/token.hpp"

/* Helper to raise error at a file */
#define KH_RAISE_ERROR(msg) {                              \
    if (!SILENT_COMPILATION)                               \
        std::wcerr << msg " in \"" << file_name << "\"\n"; \
    std::exit(1);                                          \
    }

/* Helper to raise error with more info */
#define KH_RAISE_INFO_ERROR(msg, n) \
    KH_RAISE_ERROR(msg " at " << line_n << ", " << char_line + n << ": '" << (wchar_t)chAt(i + n) << "'")


extern bool SILENT_COMPILATION;

namespace kh {
    enum class TokenizeState {
        NONE, IDENTIFIER,
        INTEGER, FLOATING, HEX, OCTAL, BIN,
        IN_BUF, IN_STR, 
        IN_INLINE_COMMENT, IN_MULTIPLE_LINE_COMMENT
    };

    std::vector<kh::Token> lex(kh::String&, const kh::String&);

    inline bool isDec(const uint32 chr) {
        return '0' <= chr && chr <= '9';
    }
    inline bool isBin(const uint32 chr) {
        return chr == '0' || chr == '1';
    }
    inline bool isOct(const uint32 chr) {
        return '0' <= chr && chr <= '7';
    }
    inline bool isHex(const uint32 chr) {
        return (('0' <= chr && chr <= '9') ||
                ('a' <= chr && chr <= 'f') ||
                ('A' <= chr && chr <= 'F'));
    }
}
