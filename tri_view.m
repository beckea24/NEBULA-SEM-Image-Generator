function out = tri_view(filename, varargin)
%TRI_VIEW  Display a Nebula (.tri) geometry file in 3D.
%
%   TRI_VIEW()               opens a file picker.
%   TRI_VIEW(FILENAME)       plots the geometry in FILENAME.
%   TRI_VIEW(...,'Name',Val) options listed below.
%   OUT = TRI_VIEW(...)      also returns the parsed geometry.
%
%   NEBULA .tri FORMAT (nebula-simulator.github.io/nebula-format-tri)
%     Plain text, one triangle per line, 11 numbers:
%         mat_in mat_out  x1 y1 z1  x2 y2 z2  x3 y3 z3
%     Coordinates are in nm, right-handed system. The normal
%         (v2 - v1) x (v3 - v1)
%     points INTO the material given by mat_out.
%     Special (negative) material IDs:
%        -122 mirror        -123 vacuum        -124 BSE detector
%        -125 SE detector   -126 detector      -127 terminator
%        -128 does nothing
%     Non-negative IDs are the materials passed on the nebula command line.
%
%   OPTIONS
%     'Hide'    - vector of material IDs; any triangle touching one of them
%                 is not drawn.  e.g. tri_view('sem.tri','Hide',[-122 -127])
%     'Only'    - vector of material IDs; draw only triangles touching them.
%     'Alpha'   - scalar face alpha for every group (default: per-group auto,
%                 solids opaque, mirrors/detectors/terminators transparent).
%     'Edges'   - true/false, draw triangle edges (default: auto).
%     'Normals' - true/false, draw outward normal arrows (default false).
%     'Axes'    - target axes handle (default: new figure).
%
%   EXAMPLES
%     tri_view('sem.tri')
%     tri_view('sem.tri','Hide',[-122 -127])        % strip the box walls
%     tri_view('sem.tri','Only',[0 1],'Normals',true)
%     g = tri_view('sem.tri');  size(g.F,1)         % triangle count

%% ---------------------------------------------------------------- inputs
if nargin < 1 || isempty(filename)
    [f, p] = uigetfile({'*.tri','Nebula geometry (*.tri)'; '*.*','All files'}, ...
                       'Select a Nebula .tri file');
    if isequal(f, 0), out = []; return; end
    filename = fullfile(p, f);
end
if exist(filename, 'file') ~= 2
    error('tri_view:noFile', 'File not found: %s', filename);
end

ip = inputParser;
ip.addParameter('Hide',    [],    @isnumeric);
ip.addParameter('Only',    [],    @isnumeric);
ip.addParameter('Alpha',   [],    @(x) isempty(x) || (isscalar(x) && x >= 0 && x <= 1));
ip.addParameter('Edges',   [],    @(x) isempty(x) || islogical(x) || isnumeric(x));
ip.addParameter('Normals', false, @(x) islogical(x) || isnumeric(x));
ip.addParameter('Axes',    [],    @(x) isempty(x) || isgraphics(x, 'axes'));
ip.parse(varargin{:});
opt = ip.Results;

%% ------------------------------------------------------------- read file
fid = fopen(filename, 'r');
if fid < 0, error('tri_view:openFailed', 'Could not open %s', filename); end
cleanup = onCleanup(@() fclose(fid));
C = textscan(fid, repmat('%f', 1, 11), 'CommentStyle', '#', 'CollectOutput', true);
clear cleanup
D = C{1};

if isempty(D)
    error('tri_view:emptyFile', 'No triangles parsed from %s.', filename);
end
if size(D, 2) ~= 11
    error('tri_view:badFormat', ...
          'Expected 11 numbers per line, got %d. Is this really a Nebula .tri file?', ...
          size(D, 2));
end

matIn  = D(:, 1);
matOut = D(:, 2);
N      = size(D, 1);

% Vertices stacked v1;v2;v3 per triangle -> (3N x 3); faces index into them.
V = reshape(D(:, 3:11).', 3, []).';
F = reshape(1:3*N, 3, []).';

%% -------------------------------------------------- normals / degeneracy
v1 = V(F(:,1), :);  v2 = V(F(:,2), :);  v3 = V(F(:,3), :);
nrm    = cross(v2 - v1, v3 - v1, 2);       % points toward mat_out
area2  = sqrt(sum(nrm.^2, 2));             % = 2 * triangle area
nDegen = nnz(area2 <= eps(max(area2)) * 10);

%% ---------------------------------------------------------------- groups
% Group by unordered material pair, so a wall drawn from either side lands
% in the same group.
pairs0 = sort([matIn matOut], 2);
[pairs, ~, gid] = unique(pairs0, 'rows');
nG = size(pairs, 1);

names  = cell(nG, 1);
cols   = zeros(nG, 3);
alphas = zeros(nG, 1);
for g = 1:nG
    a = pairs(g, 1);  b = pairs(g, 2);
    if prio(a) >= prio(b), key = a; else, key = b; end
    if a >= 0 && b >= 0 && a ~= b
        names{g} = sprintf('%s | %s', matName(a), matName(b));
    else
        names{g} = matName(key);
    end
    [cols(g, :), alphas(g)] = matStyle(key);
end
if ~isempty(opt.Alpha), alphas(:) = opt.Alpha; end

vis = true(nG, 1);
if ~isempty(opt.Only), vis = any(ismember(pairs, opt.Only(:)'), 2);     end
if ~isempty(opt.Hide), vis = vis & ~any(ismember(pairs, opt.Hide(:)'), 2); end
if ~any(vis)
    error('tri_view:nothingVisible', 'Hide/Only filters removed every triangle.');
end

%% -------------------------------------------------------------- printout
[~, base, ext] = fileparts(filename);
fprintf('\n%s%s  --  %d triangles, %d material groups\n', base, ext, N, nG);
fprintf('  bounding box (nm): x [%g %g]  y [%g %g]  z [%g %g]\n', ...
        min(V(:,1)), max(V(:,1)), min(V(:,2)), max(V(:,2)), min(V(:,3)), max(V(:,3)));
for g = 1:nG
    fprintf('  %-28s %7d tri  (%+d / %+d)%s\n', names{g}, nnz(gid == g), ...
            pairs(g,1), pairs(g,2), tern(vis(g), '', '   [hidden]'));
end
if nDegen > 0
    warning('tri_view:degenerate', ...
            '%d degenerate (zero-area) triangle(s) - nebula will ignore these.', nDegen);
end

%% ------------------------------------------------------------------ plot
if isempty(opt.Axes)
    figure('Name', ['Nebula geometry: ' base ext], 'Color', 'w');
    ax = axes();
else
    ax = opt.Axes;
end
hold(ax, 'on');

nVis = nnz(ismember(gid, find(vis)));
if isempty(opt.Edges), drawEdges = nVis <= 20000; else, drawEdges = logical(opt.Edges); end
if drawEdges, ec = [0.15 0.15 0.15]; else, ec = 'none'; end

h = gobjects(0);
for g = find(vis).'
    idx  = find(gid == g);
    rows = reshape(((idx - 1) * 3 + (1:3)).', [], 1);
    h(end+1) = patch(ax, 'Vertices', V(rows, :), ...
                         'Faces', reshape(1:3*numel(idx), 3, []).', ...
                         'FaceColor', cols(g, :), 'FaceAlpha', alphas(g), ...
                         'EdgeColor', ec, 'LineWidth', 0.25, ...
                         'DisplayName', sprintf('%s (%d)', names{g}, numel(idx))); %#ok<AGROW>
end

if opt.Normals
    keep = ismember(gid, find(vis));
    cen  = (v1 + v2 + v3) / 3;
    diag = norm([range(V(:,1)) range(V(:,2)) range(V(:,3))]);
    u    = nrm ./ max(area2, realmin) * 0.04 * diag;
    quiver3(ax, cen(keep,1), cen(keep,2), cen(keep,3), ...
                u(keep,1),   u(keep,2),   u(keep,3), 0, ...
            'Color', [0.9 0.2 0.2], 'LineWidth', 0.8, ...
            'MaxHeadSize', 0.6, 'DisplayName', 'normals (-> mat\_out)');
end

axis(ax, 'equal'); axis(ax, 'vis3d');
grid(ax, 'on'); box(ax, 'on');
xlabel(ax, 'x (nm)'); ylabel(ax, 'y (nm)'); zlabel(ax, 'z (nm)');
title(ax, sprintf('%s%s  (%d triangles)', base, ext, N), 'Interpreter', 'none');
view(ax, 40, 22);
camlight(ax, 'left'); camlight(ax, 'right');
lighting(ax, 'gouraud');
material(ax, 'dull');
legend(h, 'Location', 'eastoutside', 'Interpreter', 'none');
rotate3d(ancestor(ax, 'figure'), 'on');
hold(ax, 'off');

%% ---------------------------------------------------------------- output
if nargout > 0
    out = struct('file', filename, 'matIn', matIn, 'matOut', matOut, ...
                 'V', V, 'F', F, 'normals', nrm ./ max(area2, realmin), ...
                 'area', area2 / 2, 'groupId', gid, 'groupPairs', pairs, ...
                 'groupNames', {names});
end
end

% ======================================================================= %
function p = prio(m)
% Which material of a pair gives the group its identity/colour.
if     m >= 0,                 p = 100;   % real material wins
elseif any(m == [-124 -125 -126]), p = 80;    % detectors
elseif m == -127,              p = 60;    % terminator
elseif m == -122,              p = 50;    % mirror
elseif m == -128,              p = 20;    % no-op
else,                          p = 10;    % -123 vacuum (or unknown)
end
end

function s = matName(m)
switch m
    case -122, s = 'Mirror';
    case -123, s = 'Vacuum';
    case -124, s = 'BSE detector';
    case -125, s = 'SE detector';
    case -126, s = 'Detector';
    case -127, s = 'Terminator';
    case -128, s = 'No-op';
    otherwise
        if m >= 0, s = sprintf('Material %d', m);
        else,      s = sprintf('Unknown (%d)', m);
        end
end
end

function [c, a] = matStyle(m)
% Colour + default transparency per material class.
switch m
    case -122, c = [0.45 0.70 0.95]; a = 0.10;   % mirror  - see through it
    case -123, c = [0.80 0.80 0.80]; a = 0.05;   % vacuum
    case {-124, -125, -126}
               c = [0.20 0.70 0.40]; a = 0.25;   % detectors
    case -127, c = [0.85 0.30 0.30]; a = 0.08;   % terminator
    case -128, c = [0.60 0.60 0.60]; a = 0.10;
    otherwise
        pal = [0.72 0.74 0.78;    % 0
               0.90 0.60 0.25;    % 1
               0.45 0.55 0.85;    % 2
               0.75 0.45 0.75;    % 3
               0.55 0.75 0.55;    % 4
               0.85 0.80 0.40;    % 5
               0.50 0.75 0.80];   % 6
        c = pal(mod(max(m, 0), size(pal, 1)) + 1, :);
        a = 1.0;
end
end

function s = tern(cond, a, b)
if cond, s = a; else, s = b; end
end
