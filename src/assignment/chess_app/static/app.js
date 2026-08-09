const PIECES = {
  P: "♟",
  N: "♞",
  B: "♝",
  R: "♜",
  Q: "♛",
  K: "♚",
  p: "♟",
  n: "♞",
  b: "♝",
  r: "♜",
  q: "♛",
  k: "♚",
};

const PIECE_NAMES = {
  P: "white pawn",
  N: "white knight",
  B: "white bishop",
  R: "white rook",
  Q: "white queen",
  K: "white king",
  p: "black pawn",
  n: "black knight",
  b: "black bishop",
  r: "black rook",
  q: "black queen",
  k: "black king",
};

const files = ["a", "b", "c", "d", "e", "f", "g", "h"];
const ranks = ["8", "7", "6", "5", "4", "3", "2", "1"];

let state = null;
let selectedSquare = null;
let busy = false;
let busyStatus = "Thinking…";
let interactionStatus = null;

const boardElement = document.querySelector("#board");
const boardFrameElement = document.querySelector(".board-frame");
const statusElement = document.querySelector("#game-status");
const newGameButton = document.querySelector("#new-game");
const gameResultElement = document.querySelector("#game-result");
const resultReasonElement = document.querySelector("#result-reason");
const resultTitleElement = document.querySelector("#result-title");
const playAgainButton = document.querySelector("#play-again");
const errorElement = document.querySelector("#error-message");

async function request(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || "Move failed");
  }
  return payload;
}

function legalDestinations(square) {
  if (!state) return new Map();
  return new Map(
    state.legal_moves
      .filter((move) => move.slice(0, 2) === square)
      .map((move) => [move.slice(2, 4), move]),
  );
}

function pause(milliseconds) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

function transitionPiece(element, transform, duration, easing) {
  return new Promise((resolve) => {
    let settled = false;
    const finish = () => {
      if (settled) return;
      settled = true;
      window.clearTimeout(fallback);
      element.removeEventListener("transitionend", finish);
      resolve();
    };
    const fallback = window.setTimeout(finish, duration + 80);
    element.addEventListener("transitionend", finish, { once: true });
    window.setTimeout(() => {
      element.style.transition = `transform ${duration}ms ${easing}`;
      element.style.transform = transform;
    }, 16);
  });
}

async function animateMove(move, nextState) {
  if (!move || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    state = nextState;
    render();
    return;
  }

  const from = move.slice(0, 2);
  const to = move.slice(2, 4);
  const fromSquare = boardElement.querySelector(`[data-square="${from}"]`);
  const toSquare = boardElement.querySelector(`[data-square="${to}"]`);
  const originalPiece = fromSquare?.querySelector(".piece");

  if (!fromSquare || !toSquare || !originalPiece) {
    state = nextState;
    render();
    return;
  }

  const fromRect = fromSquare.getBoundingClientRect();
  const toRect = toSquare.getBoundingClientRect();
  const movingPiece = originalPiece.cloneNode(true);
  movingPiece.classList.add("moving-piece");
  movingPiece.style.left = `${fromRect.left}px`;
  movingPiece.style.top = `${fromRect.top}px`;
  movingPiece.style.width = `${fromRect.width}px`;
  movingPiece.style.height = `${fromRect.height}px`;
  movingPiece.style.fontSize = window.getComputedStyle(originalPiece).fontSize;

  fromSquare.classList.add("move-origin");
  if (toSquare.querySelector(".piece")) toSquare.classList.add("move-capture");
  movingPiece.style.transition = "none";
  document.body.append(movingPiece);
  movingPiece.style.transform = "translate3d(0, 0, 0) scale(1)";
  movingPiece.getBoundingClientRect();

  const distanceX = toRect.left - fromRect.left;
  const distanceY = toRect.top - fromRect.top;
  await transitionPiece(
    movingPiece,
    `translate3d(${distanceX}px, ${distanceY}px, 0) scale(1)`,
    360,
    "cubic-bezier(0.22, 0.76, 0.28, 1)",
  );
  movingPiece.remove();
  state = nextState;
  render();
}

function renderBoard() {
  boardElement.replaceChildren();
  const legal = selectedSquare ? legalDestinations(selectedSquare) : new Map();
  const lastFrom = state?.last_move?.slice(0, 2);
  const lastTo = state?.last_move?.slice(2, 4);

  ranks.forEach((rank, rankIndex) => {
    files.forEach((file, fileIndex) => {
      const squareName = `${file}${rank}`;
      const pieceCode = state?.squares[squareName];
      const pieceMoves = pieceCode ? legalDestinations(squareName) : new Map();
      const square = document.createElement("button");
      square.type = "button";
      square.className = `square ${(rankIndex + fileIndex) % 2 === 0 ? "light" : "dark"}`;
      square.dataset.square = squareName;
      square.setAttribute("role", "gridcell");
      square.setAttribute(
        "aria-label",
        pieceCode ? `${squareName}, ${PIECE_NAMES[pieceCode]}` : `${squareName}, empty`,
      );
      square.disabled = busy;

      if (squareName === selectedSquare) square.classList.add("selected");
      if (squareName === lastFrom || squareName === lastTo) square.classList.add("last-move");
      const checkedKing = state?.turn === "white" ? "K" : "k";
      if (pieceCode === checkedKing && state?.in_check) square.classList.add("checked");
      if (pieceCode && pieceCode === pieceCode.toUpperCase() && pieceMoves.size > 0) {
        square.classList.add("movable");
      }
      if (legal.has(squareName)) {
        square.classList.add("legal");
        if (pieceCode) square.classList.add("capture");
      }

      if (pieceCode) {
        const piece = document.createElement("span");
        piece.className = `piece ${pieceCode === pieceCode.toUpperCase() ? "white-piece" : "black-piece"}`;
        piece.textContent = PIECES[pieceCode];
        piece.setAttribute("aria-hidden", "true");
        square.append(piece);
      }

      if (fileIndex === 0) {
        const rankLabel = document.createElement("span");
        rankLabel.className = "coordinate rank";
        rankLabel.textContent = rank;
        square.append(rankLabel);
      }
      if (rankIndex === 7) {
        const fileLabel = document.createElement("span");
        fileLabel.className = "coordinate file";
        fileLabel.textContent = file;
        square.append(fileLabel);
      }

      square.addEventListener("click", () => handleSquareClick(squareName));
      boardElement.append(square);
    });
  });
}

function renderResult() {
  const showResult = state.game_over && !busy;
  gameResultElement.hidden = !showResult;
  boardFrameElement.classList.toggle("game-over", showResult);
  playAgainButton.disabled = busy;

  if (!showResult) return;

  const isCheckmate = state.in_check;
  resultReasonElement.textContent = isCheckmate ? "Checkmate" : "Game over";
  if (state.status === "Black wins") {
    resultTitleElement.textContent = "You lost";
  } else if (state.status === "White wins") {
    resultTitleElement.textContent = "You won";
  } else {
    resultTitleElement.textContent = "Draw";
  }
}

function render() {
  if (!state) return;
  renderBoard();
  renderResult();
  statusElement.textContent = busy ? busyStatus : interactionStatus || state.status;
  newGameButton.disabled = busy;
}

async function handleSquareClick(squareName) {
  if (busy || !state || state.game_over) return;
  errorElement.textContent = "";

  const piece = state.squares[squareName];
  const isWhitePiece = piece && piece === piece.toUpperCase();
  const legal = selectedSquare ? legalDestinations(selectedSquare) : new Map();

  if (selectedSquare && legal.has(squareName)) {
    await submitMove(legal.get(squareName));
    return;
  }

  if (isWhitePiece) {
    const moves = legalDestinations(squareName);
    if (moves.size > 0) {
      selectedSquare = squareName;
      interactionStatus = null;
    } else {
      selectedSquare = null;
      interactionStatus = state.in_check
        ? "In check — choose a defending piece"
        : "That piece has no legal move";
    }
  } else {
    selectedSquare = null;
    interactionStatus = null;
  }
  render();
}

async function submitMove(move) {
  busy = true;
  busyStatus = "Moving…";
  selectedSquare = null;
  interactionStatus = null;
  render();
  try {
    const result = await request("/api/move", {
      method: "POST",
      body: JSON.stringify({ move }),
    });
    await animateMove(result.human_move || move, result.human_state || result);
    if (result.engine_move) {
      busyStatus = "Black is moving…";
      render();
      await pause(180);
      await animateMove(result.engine_move, result);
    } else {
      state = result;
    }
  } catch (error) {
    errorElement.textContent = error.message;
    try {
      state = await request("/api/state");
    } catch (_) {
      statusElement.textContent = "Offline";
    }
  } finally {
    busy = false;
    render();
  }
}

async function startNewGame() {
  busy = true;
  busyStatus = "Starting…";
  selectedSquare = null;
  interactionStatus = null;
  errorElement.textContent = "";
  render();
  try {
    state = await request("/api/reset", { method: "POST" });
  } catch (error) {
    errorElement.textContent = error.message;
  } finally {
    busy = false;
    render();
  }
}

newGameButton.addEventListener("click", startNewGame);
playAgainButton.addEventListener("click", startNewGame);

async function initialize() {
  try {
    state = await request("/api/state");
    render();
  } catch (error) {
    statusElement.textContent = "Offline";
    errorElement.textContent = error.message;
  }
}

initialize();
