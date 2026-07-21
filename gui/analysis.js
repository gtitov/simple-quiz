document.getElementById('fileInput').addEventListener('change', handleFiles);

async function handleFiles(event) {
  const files = event.target.files;
  document.getElementById('fileCount').textContent = `Число файлов: ${files.length}`;
  let processed = 0;

  const questionErrors = {};
  const topicStats = {};
  const studentScores = [];

  for (const file of files) {
    const text = await file.text();
    const json = JSON.parse(text);
    const student = json.student;
    const questions = json.questions;
    let correct = 0;

    for (const q of questions) {
      const topic = q.topic || "Без темы";
      const questionText = q.question;
      const isCorrect = q.is_correct;

      if (isCorrect) correct++;
      else {
        if (!questionErrors[questionText]) questionErrors[questionText] = [];
        questionErrors[questionText].push({
          student,
          given: q.student_answer,
          correct: q.correct_answer,
          topic
        });
      }

      if (!topicStats[topic]) topicStats[topic] = 0;
      topicStats[topic]++;
    }

    studentScores.push({ student, correct });
    processed++;
    document.getElementById('processedCount').textContent = `Обработано файлов: ${processed}`;
  }

  drawCharts(studentScores, questionErrors, topicStats);
}

function truncate(text, len = 35) {
  return text.length > len ? text.slice(0, len) + "…" : text;
}

function surname(fullname) {
  return fullname.split(" ")[0];
}

// Wrap long hover text
function wrapText(str, width = 60) {
  return str.replace(new RegExp(`(.{${width}})`, "g"), "$1<br>");
}

// Generate stable color from topic name
function hashColor(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  let color = "#";
  for (let i = 0; i < 3; i++) {
    const value = (hash >> (i * 8)) & 0xff;
    color += ("00" + value.toString(16)).slice(-2);
  }
  return color;
}

function drawCharts(scores, errors, topics) {
  // === Chart 1 ===
  scores.sort((a, b) => b.correct - a.correct);
  Plotly.newPlot("chart1", [{
    x: scores.map(x => x.student),
    y: scores.map(x => x.correct),
    type: "bar",
    marker: { color: "lightblue" }
  }], { title: "Рейтинг студентов" });

  // === Chart 2 ===
  const sortedErrors = Object.entries(errors)
    .sort((a, b) => b[1].length - a[1].length)
    .slice(0, 50);

  const fullQuestions = sortedErrors.map(x => x[0]);
  const shortLabels = fullQuestions.map(q => truncate(q));

  const xvals = fullQuestions.map((_, i) => i);

  const colors2 = sortedErrors.map(([qText, entries]) => {
    const topic = entries[0].topic || "Без темы";
    return hashColor(topic);
  });

  const customdata = sortedErrors.map(([qText, entries]) => {
    return {
      full: wrapText(qText, 60),
      lines: entries.map(d => `${surname(d.student)}: "${d.given}"`).join("<br>")
    };
  });

  Plotly.newPlot(
    "chart2",
    [
      {
        x: xvals,
        y: sortedErrors.map(x => x[1].length),
        type: "bar",
        marker: { color: colors2 },
        customdata: customdata,
        hovertemplate:
          "<b>%{customdata.full}</b><br>%{customdata.lines}<extra></extra>"
      }
    ],
    {
      title: "Наиболее частые ошибки",
      xaxis: {
        tickmode: "array",
        tickvals: xvals,
        ticktext: shortLabels
      },
      hoverlabel: {
        namelength: -1,
        bgcolor: "rgba(255,255,255,0.95)",
        bordercolor: "#333",
        font: { size: 14 }
      }
    }
  );

  // === Chart 3 ===
  const topicsList = Object.keys(topics);
  const topicsValues = Object.values(topics);
  const colors3 = topicsList.map(t => hashColor(t));

  Plotly.newPlot("chart3", [{
    x: topicsList,
    y: topicsValues,
    type: "bar",
    marker: { color: colors3 }
  }], { title: "Анализ по темам" });
}
