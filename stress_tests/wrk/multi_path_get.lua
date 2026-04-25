local paths = {}
local counter = 0
local cookie_header = ""

local function split_paths(raw)
    for path in string.gmatch(raw, "([^,]+)") do
        table.insert(paths, path)
    end
end

function init(args)
    local raw_paths = os.getenv("WRK_PATHS") or "/"
    cookie_header = os.getenv("WRK_COOKIE") or ""
    split_paths(raw_paths)

    if #paths == 0 then
        table.insert(paths, "/")
    end
end

function request()
    local headers = {
        ["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    if cookie_header ~= "" then
        headers["Cookie"] = cookie_header
    end

    local index = (counter % #paths) + 1
    counter = counter + 1
    return wrk.format("GET", paths[index], headers)
end
