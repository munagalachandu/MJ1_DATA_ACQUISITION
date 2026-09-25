// ============================================================
// CONFIG
// ============================================================

const API_BASE = "https://mj1-data-acquisition.onrender.com/";


// ============================================================
// STATE
// ============================================================

const state = {

  semesterFiles: {},

  otherPlatforms: [],

  certManual: [],

  hackManual: [],

  achManual: []
};


// ============================================================
// ESCAPE HTML
// ============================================================

function escapeHtml(str) {

  return String(str ?? "").replace(
    /[&<>"]/g,

    c => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;"
    }[c])
  );
}


// ============================================================
// DRAG & DROP (files onto upload boxes)
// ============================================================

// Whether a dropped File matches a given <input accept="..."> value.
// Reads the *input's own* accept list rather than hardcoding "PDF or
// image" -- so the resume box (.pdf,.doc,.docx) and the PDF/image boxes
// (.pdf,image/*) are each filtered correctly with one function, no
// special-casing needed. Browsers don't always set file.type reliably on
// drop, so extension rules are checked against the filename too.
function fileMatchesAccept(file, acceptAttr) {

  const rules = (acceptAttr || "")
    .split(",")
    .map(r => r.trim().toLowerCase())
    .filter(Boolean);

  if (!rules.length) {
    return true;
  }

  const name = file.name.toLowerCase();
  const type = (file.type || "").toLowerCase();

  return rules.some(rule => {

    if (rule.startsWith(".")) {
      return name.endsWith(rule);
    }

    if (rule.endsWith("/*")) {
      return type.startsWith(rule.slice(0, -1));
    }

    return type === rule;
  });
}


// Programmatically assign a set of File objects to a real <input
// type="file">, then dispatch "change" so all the existing preview /
// state-tracking listeners (already wired to "change") fire exactly as if
// the user had picked the files from the native dialog.
function setInputFiles(input, files) {

  const dt = new DataTransfer();

  files.forEach(file => dt.items.add(file));

  input.files = dt.files;

  input.dispatchEvent(
    new Event("change", { bubbles: true })
  );
}


// Wires a drop zone to a hidden/associated file input.
//
//   dropEl   - the element the user drags over / drops onto
//   input    - the <input type="file"> to populate
//   multiple - if true, dropped files are ADDED to whatever the input
//              already holds (de-duped by name+size) instead of replacing
//              the selection -- so dropping certificates in twice, or in
//              a few batches, keeps building up the list rather than
//              wiping it out each time.
function enableDragDrop(
  dropEl,
  input,
  { multiple = false } = {}
) {

  if (!dropEl || !input) {
    return;
  }

  let dragDepth = 0;

  ["dragenter", "dragover"].forEach(evt => {

    dropEl.addEventListener(evt, event => {

      event.preventDefault();
      event.stopPropagation();

      if (evt === "dragenter") {
        dragDepth++;
      }

      dropEl.classList.add("dragging");
    });
  });

  ["dragleave", "dragend"].forEach(evt => {

    dropEl.addEventListener(evt, event => {

      event.preventDefault();
      event.stopPropagation();

      if (evt === "dragleave") {
        dragDepth = Math.max(0, dragDepth - 1);
        if (dragDepth > 0) return;
      }

      dropEl.classList.remove("dragging");
    });
  });

  dropEl.addEventListener("drop", event => {

    event.preventDefault();
    event.stopPropagation();

    dragDepth = 0;
    dropEl.classList.remove("dragging");

    const dropped = Array
      .from(event.dataTransfer?.files || [])
      .filter(file => fileMatchesAccept(file, input.accept));

    if (!dropped.length) {
      return;
    }

    if (!multiple) {
      setInputFiles(input, [dropped[0]]);
      return;
    }

    const existing = Array.from(input.files || []);

    const merged = [...existing];

    dropped.forEach(file => {

      const isDuplicate = merged.some(
        m => m.name === file.name && m.size === file.size
      );

      if (!isDuplicate) {
        merged.push(file);
      }
    });

    setInputFiles(input, merged);
  });
}


// ============================================================
// SEMESTER UPLOADS
// ============================================================

function renderSemesterUploads() {

  const count =
    Number(
      document.getElementById("semCount").value
    );


  const container =
    document.getElementById("semesterGrid");


  container.innerHTML = "";


  for (let i = 1; i <= count; i++) {

    const file =
      state.semesterFiles[i];


    const card =
      document.createElement("div");


    card.className =
      "semester-card" +
      (file ? " uploaded" : "");


    card.innerHTML = `

      <div class="semester-top">

        <div class="semester-name">
          Semester ${i}
        </div>

        <div
          class="semester-status ${
            file ? "uploaded" : ""
          }"
          id="semStatus${i}"
        >
          ${
            file
              ? "✓ Uploaded"
              : "Not uploaded"
          }
        </div>

      </div>


      <div class="semester-file">

        <label>

          <span>
            Marksheet
          </span>

          <input
            type="file"
            class="semester-input"
            data-semester="${i}"
            accept=".pdf,image/*"
          />

          <small class="drop-hint">
            or drag &amp; drop
          </small>

        </label>


        <div
          class="file-preview"
          id="semPreview${i}"
        >
          ${
            file
              ? `
                <span class="file-chip">
                  ${escapeHtml(file.name)}
                </span>
              `
              : ""
          }
        </div>

      </div>

    `;


    container.appendChild(card);


    // Each semester card is its own drop zone -- dropping a file anywhere
    // on the card (not just on the tiny native input) fills that
    // semester's marksheet. One file per semester, so replace on drop.

    enableDragDrop(
      card,
      card.querySelector(".semester-input"),
      { multiple: false }
    );
  }


  // ----------------------------------------------------------
  // IMPORTANT
  //
  // We attach listeners AFTER creating the inputs.
  //
  // When a user selects a PDF, we store the File object.
  //
  // We DO NOT call renderSemesterUploads() again.
  //
  // This prevents the browser file input from being destroyed.
  // ----------------------------------------------------------

  container
    .querySelectorAll(".semester-input")
    .forEach(input => {

      input.addEventListener(
        "change",
        event => {

          const sem =
            Number(
              event.target.dataset.semester
            );


          const file =
            event.target.files?.[0];


          if (!file) {
            return;
          }


          // Store actual File object

          state.semesterFiles[sem] =
            file;


          // Update existing card only

          const status =
            document.getElementById(
              `semStatus${sem}`
            );


          const preview =
            document.getElementById(
              `semPreview${sem}`
            );


          if (status) {

            status.textContent =
              "✓ Uploaded";

            status.classList.add(
              "uploaded"
            );
          }


          if (preview) {

            preview.innerHTML = `

              <span class="file-chip">
                ${escapeHtml(file.name)}
              </span>

            `;
          }


          event.target
            .closest(".semester-card")
            ?.classList.add("uploaded");
        }
      );
    });
}


// Change number of semesters

document
  .getElementById("semCount")
  .addEventListener(
    "change",
    () => {

      const count =
        Number(
          document.getElementById(
            "semCount"
          ).value
        );


      // Delete files belonging
      // to semesters that no longer exist

      Object.keys(
        state.semesterFiles
      ).forEach(sem => {

        if (
          Number(sem) > count
        ) {

          delete state.semesterFiles[sem];
        }
      });


      renderSemesterUploads();
    }
  );


// ============================================================
// OTHER CODING PLATFORMS
// ============================================================

function renderOtherPlatforms() {

  const container =
    document.getElementById(
      "otherPlatformsRows"
    );


  container.innerHTML = "";


  state.otherPlatforms.forEach(
    (row, index) => {

      const div =
        document.createElement("div");


      div.className =
        "platform-row";


      div.innerHTML = `

        <input
          type="text"
          placeholder="Platform"
          value="${escapeHtml(row.platform)}"
          data-index="${index}"
          data-field="platform"
        />


        <input
          type="text"
          placeholder="Username / handle"
          value="${escapeHtml(row.handle)}"
          data-index="${index}"
          data-field="handle"
        />


        <button
          type="button"
          class="btn-ghost remove-platform"
          data-index="${index}"
        >
          Remove
        </button>

      `;


      container.appendChild(div);
    }
  );


  container
    .querySelectorAll("input")
    .forEach(input => {

      input.addEventListener(
        "input",
        event => {

          const index =
            Number(
              event.target.dataset.index
            );


          const field =
            event.target.dataset.field;


          state.otherPlatforms[index][field] =
            event.target.value;
        }
      );
    });


  container
    .querySelectorAll(".remove-platform")
    .forEach(button => {

      button.addEventListener(
        "click",
        event => {

          const index =
            Number(
              event.target.dataset.index
            );


          state.otherPlatforms.splice(
            index,
            1
          );


          renderOtherPlatforms();
        }
      );
    });
}


// Quick-add platform buttons

document
  .querySelectorAll(".quick-add")
  .forEach(button => {

    button.addEventListener(
      "click",
      () => {

        state.otherPlatforms.push({

          platform:
            button.dataset.platform,

          handle: ""
        });


        renderOtherPlatforms();
      }
    );
  });


// Other platform

document
  .getElementById(
    "addPlatformBtn"
  )
  .addEventListener(
    "click",
    () => {

      state.otherPlatforms.push({

        platform: "",

        handle: ""
      });


      renderOtherPlatforms();
    }
  );


// ============================================================
// MANUAL ENTRY COMPONENT
// ============================================================

function createManualList({
  containerId,
  buttonId,
  stateKey,
  fields
}) {

  function render() {

    const container =
      document.getElementById(
        containerId
      );


    container.innerHTML = "";


    state[stateKey].forEach(
      (row, index) => {

        const div =
          document.createElement("div");


        div.className =
          "field-row";


        div.innerHTML =

          fields
            .map(field => `

              <input
                type="${field.type || "text"}"
                placeholder="${escapeHtml(field.label)}"
                value="${escapeHtml(row[field.key])}"
                data-index="${index}"
                data-field="${field.key}"
              />

            `)
            .join("")


          +

          `

            <button
              type="button"
              class="btn-ghost remove-manual"
              data-index="${index}"
            >
              ✕
            </button>

          `;


        container.appendChild(div);
      }
    );


    // Input listeners

    container
      .querySelectorAll("input")
      .forEach(input => {

        input.addEventListener(
          "input",
          event => {

            const index =
              Number(
                event.target.dataset.index
              );


            const field =
              event.target.dataset.field;


            state[stateKey][index][field] =
              event.target.value;
          }
        );
      });


    // Remove listeners

    container
      .querySelectorAll(".remove-manual")
      .forEach(button => {

        button.addEventListener(
          "click",
          event => {

            const index =
              Number(
                event.target.dataset.index
              );


            state[stateKey].splice(
              index,
              1
            );


            render();
          }
        );
      });
  }


  document
    .getElementById(buttonId)
    .addEventListener(
      "click",
      () => {

        const newRow = {};


        fields.forEach(field => {

          newRow[field.key] = "";
        });


        state[stateKey].push(
          newRow
        );


        render();
      }
    );


  render();
}


// ============================================================
// CERTIFICATIONS
// ============================================================

createManualList({

  containerId:
    "certManualRows",

  buttonId:
    "addCertManualBtn",

  stateKey:
    "certManual",

  fields: [

    {
      key: "name",
      label: "Certification name"
    },

    {
      key: "issuer",
      label: "Issuer"
    },

    {
      key: "issued_on",
      label: "Issued date",
      type: "date"
    }

  ]
});


// ============================================================
// HACKATHONS
// ============================================================

createManualList({

  containerId:
    "hackManualRows",

  buttonId:
    "addHackManualBtn",

  stateKey:
    "hackManual",

  fields: [

    {
      key: "name",
      label: "Hackathon name"
    },

    {
      key: "position",
      label: "Position / result"
    },

    {
      key: "organizer",
      label: "Organizer"
    },

    {
      key: "date",
      label: "Date",
      type: "date"
    }

  ]
});


// ============================================================
// ACHIEVEMENTS
// ============================================================

createManualList({

  containerId:
    "achManualRows",

  buttonId:
    "addAchManualBtn",

  stateKey:
    "achManual",

  fields: [

    {
      key: "title",
      label: "Achievement title"
    },

    {
      key: "description",
      label: "Description"
    },

    {
      key: "date",
      label: "Date",
      type: "date"
    }

  ]
});


// ============================================================
// MULTI-FILE PREVIEWS
// ============================================================

function setupFilePreview(
  inputId,
  previewId
) {

  const input =
    document.getElementById(
      inputId
    );


  const preview =
    document.getElementById(
      previewId
    );


  input.addEventListener(
    "change",
    () => {

      preview.innerHTML = "";


      Array
        .from(input.files)
        .forEach(file => {

          const chip =
            document.createElement(
              "span"
            );


          chip.className =
            "file-chip";


          chip.textContent =
            file.name;


          preview.appendChild(
            chip
          );
        }
      );
    }
  );
}


setupFilePreview(
  "resumeFile",
  "resumePreview"
);


setupFilePreview(
  "certFiles",
  "certPreview"
);


setupFilePreview(
  "hackFiles",
  "hackPreview"
);


setupFilePreview(
  "achFiles",
  "achPreview"
);


// ----------------------------------------------------------
// Drag & drop for the static upload boxes.
//
// Resume: single file, drop replaces the current selection.
// Certificates / hackathons / achievements: MULTIPLE files can exist per
// category (one uploaded file = one extracted entry), so drops are
// additive -- drag in a batch now, drag in more later, nothing already
// selected gets lost. Manual entries (the "+ Add ..." rows) already
// supported multiple entries and are unaffected by this.
// ----------------------------------------------------------

enableDragDrop(
  document.getElementById("resumeUploadBox"),
  document.getElementById("resumeFile"),
  { multiple: false }
);

enableDragDrop(
  document.getElementById("certUploadBox"),
  document.getElementById("certFiles"),
  { multiple: true }
);

enableDragDrop(
  document.getElementById("hackUploadBox"),
  document.getElementById("hackFiles"),
  { multiple: true }
);

enableDragDrop(
  document.getElementById("achUploadBox"),
  document.getElementById("achFiles"),
  { multiple: true }
);


// ============================================================
// SUBMIT
// ============================================================

document
  .getElementById("intakeForm")
  .addEventListener(
    "submit",
    async event => {

      event.preventDefault();


      const form =
        document.getElementById(
          "intakeForm"
        );


      const submitButton =
        document.getElementById(
          "submitBtn"
        );


      const status =
        document.getElementById(
          "submitStatus"
        );


      submitButton.disabled =
        true;


      status.className =
        "status";


      // --------------------------------------------------------
      // Count files

      const semesterFileCount =
        Object.keys(
          state.semesterFiles
        ).length;


      const resume =
        document
          .getElementById(
            "resumeFile"
          )
          .files[0];


      const certificateCount =
        document
          .getElementById(
            "certFiles"
          )
          .files.length;


      const hackathonCount =
        document
          .getElementById(
            "hackFiles"
          )
          .files.length;


      const achievementCount =
        document
          .getElementById(
            "achFiles"
          )
          .files.length;


      const totalFiles =

        semesterFileCount +

        (resume ? 1 : 0) +

        certificateCount +

        hackathonCount +

        achievementCount;


      status.textContent =
        `Preparing ${totalFiles} file${
          totalFiles === 1 ? "" : "s"
        } for extraction…`;


      // --------------------------------------------------------
      // FormData

      const fd =
        new FormData();


      // --------------------------------------------------------
      // Basic

      fd.append(
        "name",
        form.name.value
      );


      fd.append(
        "degree",
        form.degree.value
      );


      fd.append(
        "specialization",
        form.specialization.value
      );


      // --------------------------------------------------------
      // Semester files
      //
      // Each semester number is paired
      // with the corresponding file.

      Object
        .entries(
          state.semesterFiles
        )
        .sort(
          ([a], [b]) =>
            Number(a) - Number(b)
        )
        .forEach(
          ([semester, file]) => {

            fd.append(
              "semester_numbers",
              semester
            );


            fd.append(
              "semester_files",
              file
            );
          }
        );


      // --------------------------------------------------------
      // Resume

      if (resume) {

        fd.append(
          "resume_file",
          resume
        );
      }


      // --------------------------------------------------------
      // GitHub

      fd.append(
        "github_username",

        document
          .getElementById(
            "githubUsername"
          )
          .value
      );


      // --------------------------------------------------------
      // LeetCode

      fd.append(
        "leetcode_username",

        document
          .getElementById(
            "leetcodeUsername"
          )
          .value
      );


      // --------------------------------------------------------
      // Other platforms

      fd.append(

        "other_platforms_json",

        JSON.stringify(

          state.otherPlatforms
            .filter(
              p =>
                p.platform &&
                p.handle
            )

        )
      );


      // --------------------------------------------------------
      // Certifications

      Array
        .from(
          document
            .getElementById(
              "certFiles"
            )
            .files
        )
        .forEach(file => {

          fd.append(
            "certification_files",
            file
          );
        });


      // --------------------------------------------------------
      // Hackathons

      Array
        .from(
          document
            .getElementById(
              "hackFiles"
            )
            .files
        )
        .forEach(file => {

          fd.append(
            "hackathon_files",
            file
          );
        });


      // --------------------------------------------------------
      // Achievements

      Array
        .from(
          document
            .getElementById(
              "achFiles"
            )
            .files
        )
        .forEach(file => {

          fd.append(
            "achievement_files",
            file
          );
        });


      // --------------------------------------------------------
      // Manual certifications

      fd.append(

        "certifications_manual_json",

        JSON.stringify(

          state.certManual.filter(
            c => c.name
          )

        )
      );


      // --------------------------------------------------------
      // Manual hackathons

      fd.append(

        "hackathons_manual_json",

        JSON.stringify(

          state.hackManual.filter(
            h => h.name
          )

        )
      );


      // --------------------------------------------------------
      // Manual achievements

      fd.append(

        "achievements_manual_json",

        JSON.stringify(

          state.achManual.filter(
            a => a.title
          )

        )
      );


      // ========================================================
      // SEND
      // ========================================================

      try {

        const response =
          await fetch(
            `${API_BASE}/api/submit`,
            {
              method: "POST",
              body: fd
            }
          );


        if (!response.ok) {

          let message =
            `Server responded ${response.status}`;


          try {

            const error =
              await response.json();


            message =
              error.detail ||
              message;

          } catch (_) {}


          throw new Error(
            message
          );
        }


        const data =
          await response.json();


        status.textContent =
          "✓ Profile extracted successfully.";


        renderResults(data);


        document
          .getElementById(
            "results"
          )
          .scrollIntoView({
            behavior: "smooth"
          });


      } catch (error) {

        status.className =
          "status error";


        status.textContent =
          "Something went wrong: " +
          error.message;


      } finally {

        submitButton.disabled =
          false;
      }

    }
  );


// ============================================================
// PLATFORM METADATA
// ============================================================

const PLATFORM_META = {

  github: {

    label: "GitHub",

    profileUrl:
      h =>
        `https://github.com/${h}`,

    embed:
      h => `

        <img
          src="https://github-readme-stats.vercel.app/api?username=${encodeURIComponent(h)}&show_icons=true&hide_border=true&theme=github_dark_dimmed"
          height="160"
          alt="GitHub statistics"
        />

        <img
          src="https://github-readme-streak-stats.herokuapp.com/?user=${encodeURIComponent(h)}&hide_border=true&theme=github-dark-blue"
          height="160"
          alt="GitHub streak"
        />

      `
  },


  leetcode: {

    label: "LeetCode",

    profileUrl:
      h =>
        `https://leetcode.com/${encodeURIComponent(h)}`,

    embed:
      h => `

        <img
          src="https://leetcard.jacoblin.cool/${encodeURIComponent(h)}?theme=dark&font=Nunito&ext=contest"
          height="200"
          alt="LeetCode statistics"
        />

      `
  },


  codeforces: {

    label: "Codeforces",

    profileUrl:
      h =>
        `https://codeforces.com/profile/${encodeURIComponent(h)}`,

    badge:
      h =>
        `https://img.shields.io/badge/Codeforces-${encodeURIComponent(h)}?style=for-the-badge&logo=codeforces&logoColor=white`
  },


  codechef: {

    label: "CodeChef",

    profileUrl:
      h =>
        `https://www.codechef.com/users/${encodeURIComponent(h)}`,

    badge:
      h =>
        `https://img.shields.io/badge/CodeChef-${encodeURIComponent(h)}?style=for-the-badge&logo=codechef&logoColor=white`
  },


  hackerrank: {

    label: "HackerRank",

    profileUrl:
      h =>
        `https://www.hackerrank.com/profile/${encodeURIComponent(h)}`,

    badge:
      h =>
        `https://img.shields.io/badge/HackerRank-${encodeURIComponent(h)}?style=for-the-badge&logo=hackerrank&logoColor=white`
  }

};


// ============================================================
// PLATFORM RESULT HTML
// ============================================================

function platformEmbedHtml(stat) {

  const platform =
    stat.platform?.toLowerCase();


  const meta =
    PLATFORM_META[platform];


  if (!meta) {

    return `

      <div class="badge-links">

        <img
          src="https://img.shields.io/badge/${encodeURIComponent(stat.platform || "Platform")}-${encodeURIComponent(stat.handle)}-6E8B74?style=for-the-badge"
          alt="${escapeHtml(stat.platform)}"
        />

      </div>

    `;
  }


  if (meta.embed) {

    return `

      <div class="platform-embeds">

        ${meta.embed(stat.handle)}

      </div>

    `;
  }


  return `

    <div class="badge-links">

      <a
        href="${meta.profileUrl(stat.handle)}"
        target="_blank"
        rel="noopener"
      >

        <img
          src="${meta.badge(stat.handle)}"
          alt="${escapeHtml(meta.label)}"
        />

      </a>

    </div>

  `;
}


// ============================================================
// RESULTS
// ============================================================

function renderResults(data) {

  const results =
    document.getElementById(
      "results"
    );


  results.classList.remove(
    "hidden"
  );


  results.innerHTML = "";


  // Academics

  results.appendChild(

    sectionEl(

      "Academics",

      academicsHtml(
        data.academics
      )

    )

  );


  // Extraction log -- shows exactly what succeeded, was skipped, or
  // failed (and why), instead of failed items just silently missing.

  results.appendChild(

    sectionEl(
      "Extraction Log",
      sourcesLogHtml(data.sources)
    )

  );


  // Coding

  if (
    data.coding_stats?.length
  ) {

    results.appendChild(

      sectionEl(

        "Coding Platforms",

        data.coding_stats
          .map(platformEmbedHtml)
          .join("")

      )

    );
  }


  // Skills

  if (
    data.skills?.length
  ) {

    results.appendChild(

      sectionEl(

        "Skills Extracted",

        cardGrid(

          groupBy(
            data.skills,
            "skill"
          ).map(group => ({

            title:
              group.skill,

            body:
              `Found via: ${
                group.items
                  .map(
                    i => i.source
                  )
                  .join(", ")
              }`,

            tag:
              `${group.items.length} source${
                group.items.length > 1
                  ? "s"
                  : ""
              }`

          }))

        )

      )

    );
  }


  // Projects
  //
  // Rendered as a collapsible list rather than always-expanded cards --
  // GitHub accounts especially can surface a lot of repos, so each one
  // starts collapsed to just its name; opening it reveals the description
  // and the technologies used.

  if (
    data.projects?.length
  ) {

    results.appendChild(

      sectionEl(
        "Projects",
        projectListHtml(data.projects)
      )

    );
  }


  // Certifications

  if (
    data.certifications?.length
  ) {

    results.appendChild(

      sectionEl(

        "Certifications",

        cardGrid(

          data.certifications.map(
            certification => ({

              title:
                certification.name ||
                "Untitled certification",

              body:
                [
                  certification.issuer,
                  certification.issued_on
                ]
                .filter(Boolean)
                .join(" · ") ||

                "Details not clearly visible",

              tag:
                sourceTag(
                  certification.source
                )

            })
          )

        )

      )

    );
  }


  // Hackathons

  if (
    data.hackathons?.length
  ) {

    results.appendChild(

      sectionEl(

        "Hackathons",

        cardGrid(

          data.hackathons.map(
            hackathon => ({

              title:
                hackathon.name ||
                "Untitled hackathon",

              body:
                [
                  hackathon.position,
                  hackathon.organizer,
                  hackathon.date
                ]
                .filter(Boolean)
                .join(" · ") ||

                "Details not clearly visible",

              tag:
                sourceTag(
                  hackathon.source
                )

            })
          )

        )

      )

    );
  }


  // Achievements

  if (
    data.achievements?.length
  ) {

    results.appendChild(

      sectionEl(

        "Other Achievements",

        cardGrid(

          data.achievements.map(
            achievement => ({

              title:
                achievement.title ||
                "Untitled achievement",

              body:
                (
                  achievement.description ||
                  "Details not clearly visible"
                ) +

                (
                  achievement.date
                    ? `<br>${escapeHtml(
                        achievement.date
                      )}`
                    : ""
                ),

              tag:
                sourceTag(
                  achievement.source
                )

            })
          )

        )

      )

    );
  }


  // JSON

  const jsonSection =
    document.createElement(
      "div"
    );


  jsonSection.className =
    "result-section";


  jsonSection.innerHTML = `

    <h3>
      Extracted Profile (JSON)
    </h3>

    <pre class="json-dump">${
      escapeHtml(
        JSON.stringify(
          data,
          null,
          2
        )
      )
    }</pre>

  `;


  results.appendChild(
    jsonSection
  );
}


// ============================================================
// SOURCE TAG
// ============================================================

function sourceTag(source) {

  if (
    source === "manual_entry"
  ) {

    return "manually entered";
  }


  if (
    source?.endsWith("_upload")
  ) {

    return "auto-extracted";
  }


  return source || "unknown";
}


// ============================================================
// ACADEMICS HTML
// ============================================================

function academicsHtml(
  academics
) {

  if (
    !academics ||
    !academics.semesters?.length
  ) {

    return `

      <p class="hint">
        No semester marksheets were provided.
      </p>

    `;
  }


  let html = "";


  academics.semesters
    .sort(
      (a, b) =>
        a.semester - b.semester
    )
    .forEach(
      semester => {

        html += `

          <h4>
            Semester
            ${escapeHtml(
              semester.semester
            )}
          </h4>

        `;


        if (
          semester.subjects?.length
        ) {

          html += `

            <table class="marks-table">

              <thead>

                <tr>

                  <th>Code</th>

                  <th>Subject</th>

                  <th>Credits</th>

                  <th>Grade</th>

                  <th>Points</th>

                </tr>

              </thead>

              <tbody>

          `;


          semester.subjects.forEach(
            subject => {

              html += `

                <tr>

                  <td>
                    ${escapeHtml(
                      subject.code ?? "—"
                    )}
                  </td>

                  <td>
                    ${escapeHtml(
                      subject.name ?? "—"
                    )}
                  </td>

                  <td>
                    ${escapeHtml(
                      subject.credits ?? "—"
                    )}
                  </td>

                  <td>
                    ${escapeHtml(
                      subject.grade ?? "—"
                    )}
                  </td>

                  <td>
                    ${escapeHtml(
                      subject.points ?? "—"
                    )}
                  </td>

                </tr>

              `;
            }
          );


          html += `

              </tbody>

            </table>

          `;
        }


        html += `

          <div class="sgpa-line">

            SGPA:
            <b>
              ${escapeHtml(
                semester.sgpa ??
                "not detected"
              )}
            </b>

          </div>

        `;
      }
    );


  html += `

    <div class="cgpa-box">

      <div class="num">

        ${escapeHtml(
          academics.cgpa ?? "—"
        )}

      </div>

      <div class="lbl">
        Aggregate CGPA
      </div>

    </div>

  `;


  return html;
}


// ============================================================
// PROJECT LIST (collapsible)
// ============================================================

function projectListHtml(projects) {

  return `

    <div class="project-list">

      ${projects.map(project => `

        <details class="project-item">

          <summary>

            <span>
              ${escapeHtml(project.name || "Untitled project")}
            </span>

            <span class="proj-tag">
              ${escapeHtml(sourceTag(project.source))}
            </span>

            <span class="chev">▸</span>

          </summary>

          <div class="project-body">

            ${
              project.description
                ? escapeHtml(project.description)
                : "No description provided."
            }

            ${
              project.url
                ? `<br><a href="${
                    escapeHtml(project.url)
                  }" target="_blank" rel="noopener">${
                    escapeHtml(project.url)
                  }</a>`
                : ""
            }

            ${
              project.skills_used?.length
                ? `
                  <div class="tech-chips">

                    ${project.skills_used.map(skill => `
                      <span class="tech-chip">
                        ${escapeHtml(skill)}
                      </span>
                    `).join("")}

                  </div>
                `
                : ""
            }

          </div>

        </details>

      `).join("")}

    </div>

  `;
}


// ============================================================
// EXTRACTION LOG
//
// Every field the backend attempted to extract lands in
// data.sources with a status of "ok", "skipped" or "error"
// (plus a message for skipped/error). Previously nothing in
// the UI surfaced this, so a marksheet or resume that failed
// to extract just silently vanished with no explanation.
// ============================================================

function sourcesLogHtml(sources) {

  if (!sources?.length) {
    return `<p class="hint">No sources were processed.</p>`;
  }

  return `

    <div class="log-list">

      ${sources.map(entry => `

        <div class="log-row ${escapeHtml(entry.status)}">

          <span class="log-dot"></span>

          <span class="log-source">
            ${escapeHtml(entry.source)}
          </span>

          <span class="log-message">
            ${escapeHtml(entry.message || entry.status)}
          </span>

        </div>

      `).join("")}

    </div>

  `;
}


// ============================================================
// CARD GRID
// ============================================================

function cardGrid(
  items
) {

  return `

    <div class="card-grid">

      ${items.map(item => `

        <div class="info-card">

          <div class="title">

            ${escapeHtml(
              item.title
            )}

          </div>

          <div class="body">

            ${item.body}

          </div>

          <div class="tag">

            ${escapeHtml(
              item.tag
            )}

          </div>

        </div>

      `).join("")}

    </div>

  `;
}


// ============================================================
// SECTION
// ============================================================

function sectionEl(
  title,
  content
) {

  const section =
    document.createElement(
      "section"
    );


  section.className =
    "result-section";


  section.innerHTML = `

    <h3>
      ${escapeHtml(title)}
    </h3>

    ${content}

  `;


  return section;
}


// ============================================================
// GROUP BY
// ============================================================

function groupBy(
  array,
  key
) {

  const groups = {};


  array.forEach(item => {

    const value =
      item[key];


    if (
      !groups[value]
    ) {

      groups[value] = {

        [key]: value,

        items: []
      };
    }


    groups[value]
      .items
      .push(item);
  });


  return Object.values(
    groups
  );
}


// ============================================================
// INITIALIZE
// ============================================================

renderSemesterUploads();

renderOtherPlatforms();
